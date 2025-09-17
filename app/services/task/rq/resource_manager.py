# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Resource Manager

Manages memory usage, connection pooling, and cleanup procedures for RQ workers
to ensure optimal resource utilization and prevent resource leaks.
"""

import os
import logging
import threading
import time
import gc
import psutil
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import redis
from redis.connection import ConnectionPool

from app.core.security.core.security_utils import sanitize_for_log
from .production_config import ProductionRQConfig

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits configuration"""
    max_memory_mb: int = 512
    max_cpu_percent: float = 80.0
    max_connections: int = 20
    max_open_files: int = 1000
    memory_warning_threshold: float = 0.8
    cpu_warning_threshold: float = 0.7


@dataclass
class ResourceUsage:
    """Current resource usage metrics"""
    memory_mb: float
    memory_percent: float
    cpu_percent: float
    open_connections: int
    open_files: int
    timestamp: datetime


class MemoryMonitor:
    """Monitors and manages memory usage for RQ workers"""
    
    def __init__(self, limits: ResourceLimits):
        """
        Initialize memory monitor
        
        Args:
            limits: Resource limits configuration
        """
        self.limits = limits
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._callbacks: List[Callable[[ResourceUsage], None]] = []
        
        # Memory tracking
        self._memory_samples: List[float] = []
        self._max_samples = 100
        self._sample_interval = 10  # seconds
        
        # Cleanup tracking
        self._last_gc_time = time.time()
        self._gc_interval = 300  # 5 minutes
        self._cleanup_callbacks: List[Callable[[], None]] = []
    
    def start_monitoring(self) -> None:
        """Start memory monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MemoryMonitor"
        )
        self._monitor_thread.start()
        logger.info("Memory monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop memory monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info("Memory monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while not self._stop_event.wait(self._sample_interval):
            try:
                usage = self._get_current_usage()
                self._process_usage(usage)
                
                # Trigger callbacks
                for callback in self._callbacks:
                    try:
                        callback(usage)
                    except Exception as e:
                        logger.error(f"Error in memory monitor callback: {sanitize_for_log(str(e))}")
                
                # Check if cleanup is needed
                self._check_cleanup_needed(usage)
                
            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {sanitize_for_log(str(e))}")
    
    def _get_current_usage(self) -> ResourceUsage:
        """Get current resource usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Get system memory for percentage calculation
            system_memory = psutil.virtual_memory()
            
            return ResourceUsage(
                memory_mb=memory_info.rss / 1024 / 1024,
                memory_percent=(memory_info.rss / system_memory.total) * 100,
                cpu_percent=process.cpu_percent(),
                open_connections=len(process.connections()),
                open_files=process.num_fds() if hasattr(process, 'num_fds') else 0,
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            logger.error(f"Failed to get resource usage: {sanitize_for_log(str(e))}")
            return ResourceUsage(0, 0, 0, 0, 0, datetime.utcnow())
    
    def _process_usage(self, usage: ResourceUsage) -> None:
        """Process usage data and update samples"""
        # Add to memory samples
        self._memory_samples.append(usage.memory_mb)
        if len(self._memory_samples) > self._max_samples:
            self._memory_samples.pop(0)
        
        # Check limits
        if usage.memory_mb > self.limits.max_memory_mb:
            logger.warning(f"Memory usage ({usage.memory_mb:.1f}MB) exceeds limit ({self.limits.max_memory_mb}MB)")
        
        if usage.cpu_percent > self.limits.max_cpu_percent:
            logger.warning(f"CPU usage ({usage.cpu_percent:.1f}%) exceeds limit ({self.limits.max_cpu_percent}%)")
        
        # Check warning thresholds
        memory_threshold = self.limits.max_memory_mb * self.limits.memory_warning_threshold
        if usage.memory_mb > memory_threshold:
            logger.warning(f"Memory usage ({usage.memory_mb:.1f}MB) above warning threshold ({memory_threshold:.1f}MB)")
        
        cpu_threshold = self.limits.max_cpu_percent * self.limits.cpu_warning_threshold
        if usage.cpu_percent > cpu_threshold:
            logger.warning(f"CPU usage ({usage.cpu_percent:.1f}%) above warning threshold ({cpu_threshold:.1f}%)")
    
    def _check_cleanup_needed(self, usage: ResourceUsage) -> None:
        """Check if cleanup is needed and trigger if necessary"""
        current_time = time.time()
        
        # Periodic garbage collection
        if current_time - self._last_gc_time > self._gc_interval:
            self._trigger_garbage_collection()
            self._last_gc_time = current_time
        
        # Emergency cleanup if memory is too high
        memory_threshold = self.limits.max_memory_mb * 0.9  # 90% of limit
        if usage.memory_mb > memory_threshold:
            logger.warning(f"Emergency cleanup triggered - memory usage: {usage.memory_mb:.1f}MB")
            self._trigger_emergency_cleanup()
    
    def _trigger_garbage_collection(self) -> None:
        """Trigger garbage collection"""
        try:
            before_memory = self._get_current_usage().memory_mb
            
            # Force garbage collection
            collected = gc.collect()
            
            after_memory = self._get_current_usage().memory_mb
            freed_mb = before_memory - after_memory
            
            logger.info(f"Garbage collection completed: collected {collected} objects, freed {freed_mb:.1f}MB")
            
        except Exception as e:
            logger.error(f"Error during garbage collection: {sanitize_for_log(str(e))}")
    
    def _trigger_emergency_cleanup(self) -> None:
        """Trigger emergency cleanup procedures"""
        try:
            # Run garbage collection
            self._trigger_garbage_collection()
            
            # Run cleanup callbacks
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in cleanup callback: {sanitize_for_log(str(e))}")
            
            logger.info("Emergency cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during emergency cleanup: {sanitize_for_log(str(e))}")
    
    def add_usage_callback(self, callback: Callable[[ResourceUsage], None]) -> None:
        """Add callback for usage updates"""
        self._callbacks.append(callback)
    
    def add_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Add callback for cleanup procedures"""
        self._cleanup_callbacks.append(callback)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        if not self._memory_samples:
            return {}
        
        return {
            'current_mb': self._memory_samples[-1] if self._memory_samples else 0,
            'average_mb': sum(self._memory_samples) / len(self._memory_samples),
            'max_mb': max(self._memory_samples),
            'min_mb': min(self._memory_samples),
            'limit_mb': self.limits.max_memory_mb,
            'samples_count': len(self._memory_samples)
        }


class ConnectionPoolManager:
    """Manages Redis connection pools for optimal resource utilization"""
    
    def __init__(self, config: ProductionRQConfig):
        """
        Initialize connection pool manager
        
        Args:
            config: Production RQ configuration
        """
        self.config = config
        self._pools: Dict[str, ConnectionPool] = {}
        self._pool_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        # Pool configuration
        self._max_connections = int(os.getenv('RQ_CONNECTION_POOL_SIZE', '20'))
        self._max_overflow = int(os.getenv('RQ_CONNECTION_POOL_MAX_OVERFLOW', '10'))
        self._pool_timeout = int(os.getenv('RQ_CONNECTION_POOL_TIMEOUT', '30'))
        self._socket_keepalive = os.getenv('RQ_REDIS_SOCKET_KEEPALIVE', 'true').lower() == 'true'
        
        # Monitoring
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
    
    def get_connection_pool(self, pool_name: str = 'default') -> ConnectionPool:
        """
        Get or create connection pool
        
        Args:
            pool_name: Name of the connection pool
            
        Returns:
            Redis connection pool
        """
        with self._lock:
            if pool_name not in self._pools:
                self._pools[pool_name] = self._create_connection_pool(pool_name)
                self._pool_stats[pool_name] = {
                    'created_at': datetime.utcnow(),
                    'connections_created': 0,
                    'connections_closed': 0,
                    'active_connections': 0
                }
            
            return self._pools[pool_name]
    
    def _create_connection_pool(self, pool_name: str) -> ConnectionPool:
        """Create new Redis connection pool"""
        try:
            # Parse Redis URL
            redis_params = self.config.get_redis_connection_params()
            
            # Create connection pool
            pool = ConnectionPool(
                max_connections=self._max_connections,
                **redis_params
            )
            
            # Configure socket keepalive if enabled
            if self._socket_keepalive:
                pool.connection_kwargs.update({
                    'socket_keepalive': True,
                    'socket_keepalive_options': {
                        1: 1,  # TCP_KEEPIDLE
                        2: 3,  # TCP_KEEPINTVL  
                        3: 5   # TCP_KEEPCNT
                    }
                })
            
            logger.info(f"Created Redis connection pool '{pool_name}' with {self._max_connections} max connections")
            return pool
            
        except Exception as e:
            logger.error(f"Failed to create connection pool '{pool_name}': {sanitize_for_log(str(e))}")
            raise
    
    def get_redis_connection(self, pool_name: str = 'default') -> redis.Redis:
        """
        Get Redis connection from pool
        
        Args:
            pool_name: Name of the connection pool
            
        Returns:
            Redis connection
        """
        pool = self.get_connection_pool(pool_name)
        return redis.Redis(connection_pool=pool)
    
    def start_monitoring(self) -> None:
        """Start connection pool monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_pools,
            daemon=True,
            name="ConnectionPoolMonitor"
        )
        self._monitor_thread.start()
        logger.info("Connection pool monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop connection pool monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_monitoring.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info("Connection pool monitoring stopped")
    
    def _monitor_pools(self) -> None:
        """Monitor connection pools"""
        while not self._stop_monitoring.wait(30):  # Check every 30 seconds
            try:
                self._update_pool_stats()
                self._check_pool_health()
            except Exception as e:
                logger.error(f"Error monitoring connection pools: {sanitize_for_log(str(e))}")
    
    def _update_pool_stats(self) -> None:
        """Update connection pool statistics"""
        with self._lock:
            for pool_name, pool in self._pools.items():
                try:
                    stats = self._pool_stats[pool_name]
                    
                    # Update active connections count
                    stats['active_connections'] = len(pool._available_connections)
                    stats['last_updated'] = datetime.utcnow()
                    
                except Exception as e:
                    logger.error(f"Error updating stats for pool '{pool_name}': {sanitize_for_log(str(e))}")
    
    def _check_pool_health(self) -> None:
        """Check connection pool health"""
        with self._lock:
            for pool_name, pool in self._pools.items():
                try:
                    # Check if pool has too many connections
                    active_connections = len(pool._available_connections)
                    if active_connections > self._max_connections * 0.9:
                        logger.warning(f"Connection pool '{pool_name}' has {active_connections} active connections (limit: {self._max_connections})")
                    
                    # Test connection
                    conn = redis.Redis(connection_pool=pool)
                    conn.ping()
                    
                except Exception as e:
                    logger.error(f"Health check failed for pool '{pool_name}': {sanitize_for_log(str(e))}")
    
    def cleanup_pools(self) -> None:
        """Cleanup all connection pools"""
        with self._lock:
            for pool_name, pool in self._pools.items():
                try:
                    pool.disconnect()
                    logger.info(f"Disconnected connection pool '{pool_name}'")
                except Exception as e:
                    logger.error(f"Error disconnecting pool '{pool_name}': {sanitize_for_log(str(e))}")
            
            self._pools.clear()
            self._pool_stats.clear()
    
    def get_pool_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get connection pool statistics"""
        with self._lock:
            return self._pool_stats.copy()


class TaskCleanupManager:
    """Manages cleanup of completed tasks and worker resources"""
    
    def __init__(self, config: ProductionRQConfig, connection_pool_manager: ConnectionPoolManager):
        """
        Initialize task cleanup manager
        
        Args:
            config: Production RQ configuration
            connection_pool_manager: Connection pool manager
        """
        self.config = config
        self.connection_pool_manager = connection_pool_manager
        
        # Cleanup configuration
        self._cleanup_interval = int(os.getenv('RQ_CLEANUP_INTERVAL', '3600'))  # 1 hour
        self._completed_task_ttl = int(os.getenv('RQ_COMPLETED_TASK_TTL', '86400'))  # 24 hours
        self._failed_task_ttl = int(os.getenv('RQ_FAILED_TASK_TTL', '604800'))  # 7 days
        
        # Cleanup state
        self._cleanup_enabled = True
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        
        # Statistics
        self._cleanup_stats = {
            'last_cleanup': None,
            'total_cleanups': 0,
            'tasks_cleaned': 0,
            'errors': 0
        }
    
    def start_cleanup(self) -> None:
        """Start task cleanup"""
        if self._cleanup_thread:
            return
        
        self._stop_cleanup.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="TaskCleanupManager"
        )
        self._cleanup_thread.start()
        logger.info("Task cleanup started")
    
    def stop_cleanup(self) -> None:
        """Stop task cleanup"""
        if not self._cleanup_thread:
            return
        
        self._stop_cleanup.set()
        self._cleanup_thread.join(timeout=10)
        self._cleanup_thread = None
        logger.info("Task cleanup stopped")
    
    def _cleanup_loop(self) -> None:
        """Main cleanup loop"""
        while not self._stop_cleanup.wait(self._cleanup_interval):
            try:
                self._perform_cleanup()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {sanitize_for_log(str(e))}")
                self._cleanup_stats['errors'] += 1
    
    def _perform_cleanup(self) -> None:
        """Perform cleanup operations"""
        logger.info("Starting task cleanup")
        start_time = time.time()
        
        try:
            # Get Redis connection
            redis_conn = self.connection_pool_manager.get_redis_connection()
            
            # Cleanup completed tasks
            completed_cleaned = self._cleanup_completed_tasks(redis_conn)
            
            # Cleanup failed tasks
            failed_cleaned = self._cleanup_failed_tasks(redis_conn)
            
            # Cleanup job registries
            registry_cleaned = self._cleanup_job_registries(redis_conn)
            
            # Update statistics
            total_cleaned = completed_cleaned + failed_cleaned + registry_cleaned
            self._cleanup_stats.update({
                'last_cleanup': datetime.utcnow(),
                'total_cleanups': self._cleanup_stats['total_cleanups'] + 1,
                'tasks_cleaned': self._cleanup_stats['tasks_cleaned'] + total_cleaned
            })
            
            elapsed_time = time.time() - start_time
            logger.info(f"Task cleanup completed in {elapsed_time:.2f}s: {total_cleaned} tasks cleaned")
            
        except Exception as e:
            logger.error(f"Error during task cleanup: {sanitize_for_log(str(e))}")
            self._cleanup_stats['errors'] += 1
    
    def _cleanup_completed_tasks(self, redis_conn: redis.Redis) -> int:
        """Cleanup completed tasks older than TTL"""
        try:
            from rq import Queue
            from rq.registry import FinishedJobRegistry
            
            total_cleaned = 0
            cutoff_time = datetime.utcnow() - timedelta(seconds=self._completed_task_ttl)
            
            for queue_name in self.config.get_queue_names():
                queue = Queue(queue_name, connection=redis_conn)
                registry = FinishedJobRegistry(queue=queue)
                
                # Get jobs older than cutoff
                old_job_ids = []
                for job_id in registry.get_job_ids():
                    try:
                        job = queue.fetch_job(job_id)
                        if job and job.ended_at and job.ended_at < cutoff_time:
                            old_job_ids.append(job_id)
                    except Exception:
                        # Job might not exist anymore
                        old_job_ids.append(job_id)
                
                # Remove old jobs
                if old_job_ids:
                    registry.remove(*old_job_ids)
                    total_cleaned += len(old_job_ids)
                    logger.debug(f"Cleaned {len(old_job_ids)} completed tasks from queue '{queue_name}'")
            
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning completed tasks: {sanitize_for_log(str(e))}")
            return 0
    
    def _cleanup_failed_tasks(self, redis_conn: redis.Redis) -> int:
        """Cleanup failed tasks older than TTL"""
        try:
            from rq import Queue
            from rq.registry import FailedJobRegistry
            
            total_cleaned = 0
            cutoff_time = datetime.utcnow() - timedelta(seconds=self._failed_task_ttl)
            
            for queue_name in self.config.get_queue_names():
                queue = Queue(queue_name, connection=redis_conn)
                registry = FailedJobRegistry(queue=queue)
                
                # Get jobs older than cutoff
                old_job_ids = []
                for job_id in registry.get_job_ids():
                    try:
                        job = queue.fetch_job(job_id)
                        if job and job.ended_at and job.ended_at < cutoff_time:
                            old_job_ids.append(job_id)
                    except Exception:
                        # Job might not exist anymore
                        old_job_ids.append(job_id)
                
                # Remove old jobs
                if old_job_ids:
                    registry.remove(*old_job_ids)
                    total_cleaned += len(old_job_ids)
                    logger.debug(f"Cleaned {len(old_job_ids)} failed tasks from queue '{queue_name}'")
            
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning failed tasks: {sanitize_for_log(str(e))}")
            return 0
    
    def _cleanup_job_registries(self, redis_conn: redis.Redis) -> int:
        """Cleanup job registries"""
        try:
            # This would implement cleanup of various RQ registries
            # For now, just return 0 as a placeholder
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning job registries: {sanitize_for_log(str(e))}")
            return 0
    
    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics"""
        return self._cleanup_stats.copy()


class RQResourceManager:
    """Main resource manager for RQ workers"""
    
    def __init__(self, config: ProductionRQConfig):
        """
        Initialize RQ resource manager
        
        Args:
            config: Production RQ configuration
        """
        self.config = config
        
        # Initialize resource limits
        self.limits = ResourceLimits(
            max_memory_mb=config.worker_memory_limit,
            max_cpu_percent=80.0,
            max_connections=20,
            memory_warning_threshold=0.8,
            cpu_warning_threshold=0.7
        )
        
        # Initialize components
        self.memory_monitor = MemoryMonitor(self.limits)
        self.connection_pool_manager = ConnectionPoolManager(config)
        self.cleanup_manager = TaskCleanupManager(config, self.connection_pool_manager)
        
        # Resource manager state
        self._started = False
    
    def start(self) -> None:
        """Start resource management"""
        if self._started:
            return
        
        logger.info("Starting RQ resource management")
        
        # Start memory monitoring
        self.memory_monitor.start_monitoring()
        
        # Start connection pool monitoring
        self.connection_pool_manager.start_monitoring()
        
        # Start task cleanup
        self.cleanup_manager.start_cleanup()
        
        self._started = True
        logger.info("RQ resource management started")
    
    def stop(self) -> None:
        """Stop resource management"""
        if not self._started:
            return
        
        logger.info("Stopping RQ resource management")
        
        # Stop task cleanup
        self.cleanup_manager.stop_cleanup()
        
        # Stop connection pool monitoring
        self.connection_pool_manager.stop_monitoring()
        
        # Stop memory monitoring
        self.memory_monitor.stop_monitoring()
        
        # Cleanup connection pools
        self.connection_pool_manager.cleanup_pools()
        
        self._started = False
        logger.info("RQ resource management stopped")
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get resource management status"""
        return {
            'started': self._started,
            'memory_stats': self.memory_monitor.get_memory_stats(),
            'pool_stats': self.connection_pool_manager.get_pool_stats(),
            'cleanup_stats': self.cleanup_manager.get_cleanup_stats(),
            'limits': {
                'max_memory_mb': self.limits.max_memory_mb,
                'max_cpu_percent': self.limits.max_cpu_percent,
                'max_connections': self.limits.max_connections
            }
        }
    
    def trigger_cleanup(self) -> None:
        """Manually trigger cleanup operations"""
        logger.info("Manually triggering resource cleanup")
        
        # Trigger memory cleanup
        self.memory_monitor._trigger_emergency_cleanup()
        
        # Trigger task cleanup
        self.cleanup_manager._perform_cleanup()
        
        logger.info("Manual resource cleanup completed")
    
    def get_redis_connection(self, pool_name: str = 'default') -> redis.Redis:
        """Get Redis connection from managed pool"""
        return self.connection_pool_manager.get_redis_connection(pool_name)
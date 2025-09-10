# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Background Cleanup Manager for Multi-Tenant Caption Management

This module provides background cleanup tasks for old audit logs, metrics,
expired cache entries, and other maintenance operations to keep the system
running efficiently.
"""

import logging
import threading
import time
import redis
import json
import psutil
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
from sqlalchemy import and_, func, text
from sqlalchemy.exc import SQLAlchemyError

from database import DatabaseManager
from models import JobAuditLog, CaptionGenerationTask, TaskStatus, ProcessingRun, User
from performance_cache_manager import PerformanceCacheManager, CacheKeyGenerator
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

@dataclass
class CleanupConfig:
    """Configuration for cleanup operations"""
    audit_log_retention_days: int = 90
    metrics_retention_days: int = 30
    failed_task_retention_days: int = 30
    completed_task_retention_days: int = 365
    cache_cleanup_interval_minutes: int = 60
    database_cleanup_interval_hours: int = 24
    max_cleanup_batch_size: int = 1000
    cleanup_enabled: bool = True

class TaskHealthStatus(Enum):
    """Health status for background tasks"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"

@dataclass
class CleanupStats:
    """Statistics from cleanup operations"""
    operation_name: str
    items_cleaned: int
    execution_time_seconds: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

@dataclass
class TaskHealthMetrics:
    """Health metrics for background tasks"""
    task_name: str
    status: TaskHealthStatus
    last_run: datetime
    execution_count: int
    success_count: int
    failure_count: int
    avg_execution_time: float
    last_error: Optional[str]
    resource_usage: Dict[str, float]
    timestamp: datetime

@dataclass
class TaskCoordinationInfo:
    """Information about task coordination"""
    task_name: str
    thread_id: str
    is_running: bool
    start_time: datetime
    last_heartbeat: datetime
    resource_limits: Dict[str, Any]
    dependencies: List[str]

class BackgroundCleanupManager:
    """Manages background cleanup tasks for system maintenance with health monitoring and task coordination"""
    
    def __init__(self, db_manager: DatabaseManager, redis_client: redis.Redis,
                 cache_manager: Optional[PerformanceCacheManager] = None,
                 config: Optional[CleanupConfig] = None,
                 notification_monitor: Optional[Any] = None):
        """
        Initialize background cleanup manager
        
        Args:
            db_manager: Database manager instance
            redis_client: Redis client for cache cleanup
            cache_manager: Optional cache manager instance
            config: Cleanup configuration
            notification_monitor: Optional notification system monitor for integration
        """
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.cache_manager = cache_manager
        self.config = config or CleanupConfig()
        self.notification_monitor = notification_monitor
        
        self._cleanup_stats = []
        self._cleanup_threads = {}
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()
        
        # Health monitoring attributes
        self._task_health_metrics = {}
        self._task_coordination_info = {}
        self._health_check_interval = 60  # seconds
        self._health_monitor_thread = None
        self._resource_monitors = {}
        self._task_dependencies = {}
        self._heartbeat_timeout = 300  # 5 minutes
        
        # Task coordination attributes
        self._task_locks = {}
        self._task_queues = defaultdict(deque)
        self._task_priorities = {}
        self._max_concurrent_tasks = 3
        self._running_tasks = set()
        
        # Performance tracking
        self._execution_history = defaultdict(deque)
        self._resource_usage_history = defaultdict(deque)
        self._error_history = defaultdict(deque)
        
        # Register cleanup tasks with dependencies
        self._cleanup_tasks = {
            'audit_logs': self._cleanup_old_audit_logs,
            'failed_tasks': self._cleanup_old_failed_tasks,
            'completed_tasks': self._cleanup_old_completed_tasks,
            'cache_entries': self._cleanup_expired_cache_entries,
            'processing_runs': self._cleanup_old_processing_runs,
            'orphaned_data': self._cleanup_orphaned_data
        }
        
        # Define task dependencies (tasks that should run before others)
        self._task_dependencies = {
            'orphaned_data': ['audit_logs', 'failed_tasks', 'completed_tasks'],
            'cache_entries': [],  # No dependencies
            'processing_runs': ['completed_tasks'],
            'audit_logs': [],
            'failed_tasks': [],
            'completed_tasks': []
        }
        
        # Initialize task locks
        for task_name in self._cleanup_tasks:
            self._task_locks[task_name] = threading.Lock()
    
    def start_background_cleanup(self):
        """Start background cleanup threads with health monitoring and task coordination"""
        if not self.config.cleanup_enabled:
            logger.info("Background cleanup is disabled")
            return
        
        logger.info("Starting enhanced background cleanup manager with health monitoring")
        
        # Start health monitoring thread first
        self._health_monitor_thread = threading.Thread(
            target=self._health_monitoring_loop,
            daemon=True,
            name="CleanupHealthMonitor"
        )
        self._health_monitor_thread.start()
        
        # Start cache cleanup thread (runs more frequently)
        cache_thread = threading.Thread(
            target=self._run_coordinated_cleanup,
            args=('cache_cleanup', self._cleanup_expired_cache_entries, 
                  self.config.cache_cleanup_interval_minutes * 60),
            daemon=True,
            name="CacheCleanupTask"
        )
        cache_thread.start()
        self._cleanup_threads['cache_cleanup'] = cache_thread
        
        # Initialize coordination info for cache cleanup
        self._task_coordination_info['cache_cleanup'] = TaskCoordinationInfo(
            task_name='cache_cleanup',
            thread_id=str(cache_thread.ident),
            is_running=True,
            start_time=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc),
            resource_limits={'memory_mb': 100, 'cpu_percent': 10},
            dependencies=[]
        )
        
        # Start database cleanup thread (runs less frequently)
        db_thread = threading.Thread(
            target=self._run_coordinated_cleanup,
            args=('database_cleanup', self._run_all_database_cleanup,
                  self.config.database_cleanup_interval_hours * 3600),
            daemon=True,
            name="DatabaseCleanupTask"
        )
        db_thread.start()
        self._cleanup_threads['database_cleanup'] = db_thread
        
        # Initialize coordination info for database cleanup
        self._task_coordination_info['database_cleanup'] = TaskCoordinationInfo(
            task_name='database_cleanup',
            thread_id=str(db_thread.ident),
            is_running=True,
            start_time=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc),
            resource_limits={'memory_mb': 500, 'cpu_percent': 20},
            dependencies=list(self._task_dependencies.get('database_cleanup', []))
        )
        
        # Initialize health metrics for all tasks
        for task_name in ['cache_cleanup', 'database_cleanup']:
            self._task_health_metrics[task_name] = TaskHealthMetrics(
                task_name=task_name,
                status=TaskHealthStatus.HEALTHY,
                last_run=datetime.now(timezone.utc),
                execution_count=0,
                success_count=0,
                failure_count=0,
                avg_execution_time=0.0,
                last_error=None,
                resource_usage={'memory_mb': 0, 'cpu_percent': 0},
                timestamp=datetime.now(timezone.utc)
            )
        
        logger.info(f"Started {len(self._cleanup_threads)} background cleanup threads with health monitoring")
    
    def stop_background_cleanup(self):
        """Stop all background cleanup threads with graceful shutdown tracking"""
        logger.info("Stopping enhanced background cleanup manager")
        self._shutdown_event.set()
        
        # Track shutdown progress
        shutdown_start = datetime.now()
        shutdown_timeout = 30  # seconds
        
        # Stop health monitoring thread first
        if self._health_monitor_thread and self._health_monitor_thread.is_alive():
            logger.info("Stopping health monitoring thread...")
            self._health_monitor_thread.join(timeout=5)
            if self._health_monitor_thread.is_alive():
                logger.warning("Health monitoring thread did not finish gracefully")
        
        # Wait for cleanup threads to finish with enhanced tracking
        for thread_name, thread in self._cleanup_threads.items():
            if thread.is_alive():
                logger.info(f"Waiting for {thread_name} thread to finish...")
                
                # Update coordination info
                if thread_name in self._task_coordination_info:
                    self._task_coordination_info[thread_name].is_running = False
                
                # Wait with timeout
                thread.join(timeout=shutdown_timeout)
                
                if thread.is_alive():
                    logger.warning(f"Thread {thread_name} did not finish gracefully within {shutdown_timeout}s")
                    
                    # Update health metrics to reflect forced shutdown
                    if thread_name in self._task_health_metrics:
                        self._task_health_metrics[thread_name].status = TaskHealthStatus.FAILED
                        self._task_health_metrics[thread_name].last_error = "Forced shutdown - thread did not terminate gracefully"
                else:
                    logger.info(f"Thread {thread_name} stopped gracefully")
        
        # Clear all tracking data
        self._cleanup_threads.clear()
        self._running_tasks.clear()
        
        # Calculate total shutdown time
        shutdown_time = (datetime.now() - shutdown_start).total_seconds()
        
        # Notify notification monitor if available
        if self.notification_monitor:
            try:
                self.notification_monitor._error_counts['cleanup_shutdown'] = 1 if shutdown_time > shutdown_timeout else 0
            except Exception as e:
                logger.warning(f"Failed to notify notification monitor of shutdown: {e}")
        
        logger.info(f"Background cleanup manager stopped (shutdown time: {shutdown_time:.2f}s)")
    
    def _run_coordinated_cleanup(self, task_name: str, cleanup_func: Callable, interval_seconds: int):
        """Run a cleanup function periodically with coordination and health monitoring"""
        logger.info(f"Started coordinated cleanup task: {task_name} (interval: {interval_seconds}s)")
        
        while not self._shutdown_event.is_set():
            try:
                # Check if we can run (coordination check)
                if not self._can_run_task(task_name):
                    logger.debug(f"Task {task_name} waiting for coordination clearance")
                    self._shutdown_event.wait(30)  # Wait 30 seconds before checking again
                    continue
                
                # Add to running tasks
                self._running_tasks.add(task_name)
                
                # Update heartbeat
                self._update_task_heartbeat(task_name)
                
                # Monitor resource usage before execution
                initial_memory = self._get_process_memory_usage()
                initial_cpu = psutil.cpu_percent(interval=0.1)
                
                start_time = datetime.now()
                result = cleanup_func()
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Monitor resource usage after execution
                final_memory = self._get_process_memory_usage()
                final_cpu = psutil.cpu_percent(interval=0.1)
                
                # Calculate resource usage
                memory_used = max(0, final_memory - initial_memory)
                cpu_used = max(0, final_cpu - initial_cpu)
                
                # Update health metrics
                self._update_task_health_metrics(task_name, True, execution_time, memory_used, cpu_used)
                
                # Record stats
                stats = CleanupStats(
                    operation_name=task_name,
                    items_cleaned=result if isinstance(result, int) else 0,
                    execution_time_seconds=execution_time,
                    timestamp=start_time,
                    success=True
                )
                self._record_cleanup_stats(stats)
                
                if result and isinstance(result, int) and result > 0:
                    logger.info(f"Coordinated cleanup task {task_name} completed: {result} items cleaned in {execution_time:.2f}s (Memory: +{memory_used:.1f}MB, CPU: +{cpu_used:.1f}%)")
                
                # Notify notification monitor if available
                if self.notification_monitor:
                    try:
                        self.notification_monitor._error_counts[f'cleanup_{task_name}_success'] = self.notification_monitor._error_counts.get(f'cleanup_{task_name}_success', 0) + 1
                    except Exception:
                        pass  # Don't fail cleanup if notification fails
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error in coordinated cleanup task {task_name}: {sanitize_for_log(error_msg)}")
                
                # Update health metrics for failure
                self._update_task_health_metrics(task_name, False, 0, 0, 0, error_msg)
                
                # Record error stats
                stats = CleanupStats(
                    operation_name=task_name,
                    items_cleaned=0,
                    execution_time_seconds=0,
                    timestamp=datetime.now(),
                    success=False,
                    error_message=error_msg
                )
                self._record_cleanup_stats(stats)
                
                # Notify notification monitor of error
                if self.notification_monitor:
                    try:
                        self.notification_monitor._error_counts[f'cleanup_{task_name}_error'] = self.notification_monitor._error_counts.get(f'cleanup_{task_name}_error', 0) + 1
                    except Exception:
                        pass
            
            finally:
                # Remove from running tasks
                self._running_tasks.discard(task_name)
            
            # Wait for next interval or shutdown
            self._shutdown_event.wait(interval_seconds)
    
    def _run_all_database_cleanup(self) -> int:
        """Run all database cleanup tasks"""
        total_cleaned = 0
        
        for task_name, cleanup_func in self._cleanup_tasks.items():
            if task_name == 'cache_entries':
                continue  # Skip cache cleanup in database cleanup
            
            try:
                cleaned = cleanup_func()
                if isinstance(cleaned, int):
                    total_cleaned += cleaned
            except Exception as e:
                logger.error(f"Error in database cleanup task {task_name}: {sanitize_for_log(str(e))}")
        
        return total_cleaned
    
    def _cleanup_old_audit_logs(self) -> int:
        """Clean up old audit log entries"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config.audit_log_retention_days)
        
        with self.db_manager.get_session() as session:
            try:
                # Delete in batches to avoid long-running transactions
                total_deleted = 0
                batch_size = self.config.max_cleanup_batch_size
                
                while True:
                    # Get batch of old audit logs
                    old_logs = session.query(JobAuditLog).filter(
                        JobAuditLog.timestamp < cutoff_date
                    ).limit(batch_size).all()
                    
                    if not old_logs:
                        break
                    
                    # Delete batch
                    for log in old_logs:
                        session.delete(log)
                    
                    session.commit()
                    total_deleted += len(old_logs)
                    
                    # Break if we got less than a full batch
                    if len(old_logs) < batch_size:
                        break
                
                if total_deleted > 0:
                    logger.info(f"Cleaned up {total_deleted} old audit log entries")
                
                return total_deleted
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error cleaning up audit logs: {sanitize_for_log(str(e))}")
                raise
    
    def _cleanup_old_failed_tasks(self) -> int:
        """Clean up old failed task records"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config.failed_task_retention_days)
        
        with self.db_manager.get_session() as session:
            try:
                # Delete old failed tasks in batches
                total_deleted = 0
                batch_size = self.config.max_cleanup_batch_size
                
                while True:
                    old_tasks = session.query(CaptionGenerationTask).filter(
                        and_(
                            CaptionGenerationTask.status == TaskStatus.FAILED,
                            CaptionGenerationTask.completed_at < cutoff_date
                        )
                    ).limit(batch_size).all()
                    
                    if not old_tasks:
                        break
                    
                    # Delete batch
                    for task in old_tasks:
                        session.delete(task)
                    
                    session.commit()
                    total_deleted += len(old_tasks)
                    
                    if len(old_tasks) < batch_size:
                        break
                
                if total_deleted > 0:
                    logger.info(f"Cleaned up {total_deleted} old failed task records")
                
                return total_deleted
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error cleaning up failed tasks: {sanitize_for_log(str(e))}")
                raise
    
    def _cleanup_old_completed_tasks(self) -> int:
        """Clean up old completed task records (keep longer than failed tasks)"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config.completed_task_retention_days)
        
        with self.db_manager.get_session() as session:
            try:
                # Delete old completed tasks in batches
                total_deleted = 0
                batch_size = self.config.max_cleanup_batch_size
                
                while True:
                    old_tasks = session.query(CaptionGenerationTask).filter(
                        and_(
                            CaptionGenerationTask.status == TaskStatus.COMPLETED,
                            CaptionGenerationTask.completed_at < cutoff_date
                        )
                    ).limit(batch_size).all()
                    
                    if not old_tasks:
                        break
                    
                    # Delete batch
                    for task in old_tasks:
                        session.delete(task)
                    
                    session.commit()
                    total_deleted += len(old_tasks)
                    
                    if len(old_tasks) < batch_size:
                        break
                
                if total_deleted > 0:
                    logger.info(f"Cleaned up {total_deleted} old completed task records")
                
                return total_deleted
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error cleaning up completed tasks: {sanitize_for_log(str(e))}")
                raise
    
    def _cleanup_old_processing_runs(self) -> int:
        """Clean up old processing run records"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config.metrics_retention_days)
        
        with self.db_manager.get_session() as session:
            try:
                # Delete old processing runs
                deleted_count = session.query(ProcessingRun).filter(
                    ProcessingRun.created_at < cutoff_date
                ).delete()
                
                session.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old processing run records")
                
                return deleted_count
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error cleaning up processing runs: {sanitize_for_log(str(e))}")
                raise
    
    def _cleanup_expired_cache_entries(self) -> int:
        """Clean up expired cache entries from Redis"""
        try:
            # Get all cache keys
            cache_pattern = f"{CacheKeyGenerator.PREFIX}*"
            cache_keys = self.redis_client.keys(cache_pattern)
            
            if not cache_keys:
                return 0
            
            # Check which keys are expired and clean them up
            expired_keys = []
            for key in cache_keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired and removed)
                    expired_keys.append(key)
                elif ttl == -1:  # Key exists but has no expiration
                    # Check if it's an old key that should have expiration
                    try:
                        data = self.redis_client.get(key)
                        if data:
                            cache_entry = json.loads(data)
                            if isinstance(cache_entry, dict) and 'cached_at' in cache_entry:
                                cached_at = datetime.fromisoformat(cache_entry['cached_at'])
                                if datetime.now(timezone.utc) - cached_at > timedelta(hours=24):
                                    expired_keys.append(key)
                    except Exception:
                        # If we can't parse the data, consider it expired
                        expired_keys.append(key)
            
            # Delete expired keys
            if expired_keys:
                deleted_count = self.redis_client.delete(*expired_keys)
                logger.debug(f"Cleaned up {deleted_count} expired cache entries")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning up cache entries: {sanitize_for_log(str(e))}")
            raise
    
    def _cleanup_orphaned_data(self) -> int:
        """Clean up orphaned data (tasks without users, etc.)"""
        with self.db_manager.get_session() as session:
            try:
                # Find tasks with non-existent users
                orphaned_tasks = session.query(CaptionGenerationTask).filter(
                    ~CaptionGenerationTask.user_id.in_(
                        session.query(User.id)
                    )
                ).all()
                
                total_cleaned = 0
                
                # Delete orphaned tasks
                for task in orphaned_tasks:
                    session.delete(task)
                    total_cleaned += 1
                
                # Find audit logs with non-existent tasks
                orphaned_audit_logs = session.query(JobAuditLog).filter(
                    and_(
                        JobAuditLog.task_id.isnot(None),
                        ~JobAuditLog.task_id.in_(
                            session.query(CaptionGenerationTask.id)
                        )
                    )
                ).all()
                
                # Delete orphaned audit logs
                for log in orphaned_audit_logs:
                    session.delete(log)
                    total_cleaned += 1
                
                session.commit()
                
                if total_cleaned > 0:
                    logger.info(f"Cleaned up {total_cleaned} orphaned data records")
                
                return total_cleaned
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error cleaning up orphaned data: {sanitize_for_log(str(e))}")
                raise
    
    def run_manual_cleanup(self, cleanup_type: str) -> Dict[str, Any]:
        """
        Run a specific cleanup task manually
        
        Args:
            cleanup_type: Type of cleanup to run
            
        Returns:
            Dictionary with cleanup results
        """
        if cleanup_type not in self._cleanup_tasks:
            return {
                'success': False,
                'error': f'Unknown cleanup type: {cleanup_type}',
                'available_types': list(self._cleanup_tasks.keys())
            }
        
        start_time = datetime.now()
        
        try:
            cleanup_func = self._cleanup_tasks[cleanup_type]
            items_cleaned = cleanup_func()
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Record stats
            stats = CleanupStats(
                operation_name=f'manual_{cleanup_type}',
                items_cleaned=items_cleaned if isinstance(items_cleaned, int) else 0,
                execution_time_seconds=execution_time,
                timestamp=start_time,
                success=True
            )
            self._record_cleanup_stats(stats)
            
            return {
                'success': True,
                'cleanup_type': cleanup_type,
                'items_cleaned': items_cleaned,
                'execution_time_seconds': execution_time,
                'timestamp': start_time.isoformat()
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            
            # Record error stats
            stats = CleanupStats(
                operation_name=f'manual_{cleanup_type}',
                items_cleaned=0,
                execution_time_seconds=execution_time,
                timestamp=start_time,
                success=False,
                error_message=error_msg
            )
            self._record_cleanup_stats(stats)
            
            logger.error(f"Error in manual cleanup {cleanup_type}: {sanitize_for_log(error_msg)}")
            
            return {
                'success': False,
                'cleanup_type': cleanup_type,
                'error': error_msg,
                'execution_time_seconds': execution_time,
                'timestamp': start_time.isoformat()
            }
    
    def get_cleanup_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get enhanced cleanup statistics with health monitoring data
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with comprehensive cleanup statistics and health data
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_stats = [s for s in self._cleanup_stats if s.timestamp >= cutoff_time]
        
        if not recent_stats:
            return {
                'message': f'No cleanup statistics available for the last {hours} hours',
                'health_monitoring': self.monitor_task_health(),
                'task_coordination': self.coordinate_cleanup_tasks(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Calculate summary statistics
        total_operations = len(recent_stats)
        successful_operations = sum(1 for s in recent_stats if s.success)
        total_items_cleaned = sum(s.items_cleaned for s in recent_stats)
        total_execution_time = sum(s.execution_time_seconds for s in recent_stats)
        
        # Group by operation type
        operation_stats = {}
        for stat in recent_stats:
            if stat.operation_name not in operation_stats:
                operation_stats[stat.operation_name] = {
                    'count': 0,
                    'items_cleaned': 0,
                    'total_time': 0,
                    'success_count': 0,
                    'last_run': None
                }
            
            op_stat = operation_stats[stat.operation_name]
            op_stat['count'] += 1
            op_stat['items_cleaned'] += stat.items_cleaned
            op_stat['total_time'] += stat.execution_time_seconds
            if stat.success:
                op_stat['success_count'] += 1
            
            if not op_stat['last_run'] or stat.timestamp > op_stat['last_run']:
                op_stat['last_run'] = stat.timestamp.isoformat()
        
        # Calculate averages
        for op_name, op_stat in operation_stats.items():
            op_stat['avg_time'] = op_stat['total_time'] / op_stat['count']
            op_stat['success_rate'] = (op_stat['success_count'] / op_stat['count']) * 100
        
        return {
            'summary': {
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'success_rate': (successful_operations / total_operations) * 100,
                'total_items_cleaned': total_items_cleaned,
                'total_execution_time_seconds': total_execution_time,
                'avg_execution_time_seconds': total_execution_time / total_operations
            },
            'operation_breakdown': operation_stats,
            'active_threads': list(self._cleanup_threads.keys()),
            'health_monitoring': self.monitor_task_health(),
            'task_coordination': self.coordinate_cleanup_tasks(),
            'notification_integration': {
                'monitor_available': self.notification_monitor is not None,
                'integration_active': self.notification_monitor is not None and hasattr(self.notification_monitor, '_error_counts')
            },
            'config': {
                'cleanup_enabled': self.config.cleanup_enabled,
                'audit_log_retention_days': self.config.audit_log_retention_days,
                'metrics_retention_days': self.config.metrics_retention_days,
                'cache_cleanup_interval_minutes': self.config.cache_cleanup_interval_minutes,
                'database_cleanup_interval_hours': self.config.database_cleanup_interval_hours,
                'max_concurrent_tasks': self._max_concurrent_tasks,
                'health_check_interval': self._health_check_interval,
                'heartbeat_timeout': self._heartbeat_timeout
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _record_cleanup_stats(self, stats: CleanupStats):
        """Record cleanup statistics"""
        with self._lock:
            self._cleanup_stats.append(stats)
            
            # Keep only last 1000 stats
            if len(self._cleanup_stats) > 1000:
                self._cleanup_stats = self._cleanup_stats[-1000:]
    
    def _health_monitoring_loop(self):
        """Health monitoring loop for background tasks"""
        logger.info("Started cleanup task health monitoring loop")
        
        while not self._shutdown_event.is_set():
            try:
                self._check_task_health()
                self._check_resource_usage()
                self._check_task_heartbeats()
                
                # Integrate with notification monitor if available
                if self.notification_monitor:
                    self._integrate_with_notification_monitor()
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {sanitize_for_log(str(e))}")
            
            # Wait for next health check
            self._shutdown_event.wait(self._health_check_interval)
    
    def _can_run_task(self, task_name: str) -> bool:
        """Check if a task can run based on coordination rules"""
        # Check if too many tasks are running
        if len(self._running_tasks) >= self._max_concurrent_tasks:
            return False
        
        # Check dependencies
        dependencies = self._task_dependencies.get(task_name, [])
        for dep_task in dependencies:
            if dep_task in self._running_tasks:
                return False
        
        # Check resource limits
        if task_name in self._task_coordination_info:
            coord_info = self._task_coordination_info[task_name]
            current_memory = self._get_process_memory_usage()
            current_cpu = psutil.cpu_percent(interval=0.1)
            
            # Check if we would exceed resource limits
            memory_limit = coord_info.resource_limits.get('memory_mb', 1000)
            cpu_limit = coord_info.resource_limits.get('cpu_percent', 50)
            
            if current_memory > memory_limit * 0.8 or current_cpu > cpu_limit * 0.8:
                return False
        
        return True
    
    def _update_task_heartbeat(self, task_name: str):
        """Update task heartbeat timestamp"""
        if task_name in self._task_coordination_info:
            self._task_coordination_info[task_name].last_heartbeat = datetime.now(timezone.utc)
    
    def _update_task_health_metrics(self, task_name: str, success: bool, execution_time: float, 
                                   memory_used: float, cpu_used: float, error_msg: Optional[str] = None):
        """Update health metrics for a task"""
        if task_name not in self._task_health_metrics:
            self._task_health_metrics[task_name] = TaskHealthMetrics(
                task_name=task_name,
                status=TaskHealthStatus.HEALTHY,
                last_run=datetime.now(timezone.utc),
                execution_count=0,
                success_count=0,
                failure_count=0,
                avg_execution_time=0.0,
                last_error=None,
                resource_usage={'memory_mb': 0, 'cpu_percent': 0},
                timestamp=datetime.now(timezone.utc)
            )
        
        metrics = self._task_health_metrics[task_name]
        metrics.last_run = datetime.now(timezone.utc)
        metrics.execution_count += 1
        
        if success:
            metrics.success_count += 1
            metrics.status = TaskHealthStatus.HEALTHY
        else:
            metrics.failure_count += 1
            metrics.last_error = error_msg
            
            # Determine status based on failure rate
            failure_rate = metrics.failure_count / metrics.execution_count
            if failure_rate > 0.5:
                metrics.status = TaskHealthStatus.CRITICAL
            elif failure_rate > 0.2:
                metrics.status = TaskHealthStatus.WARNING
        
        # Update average execution time
        if execution_time > 0:
            if metrics.avg_execution_time == 0:
                metrics.avg_execution_time = execution_time
            else:
                metrics.avg_execution_time = (metrics.avg_execution_time * 0.8) + (execution_time * 0.2)
        
        # Update resource usage
        metrics.resource_usage = {
            'memory_mb': memory_used,
            'cpu_percent': cpu_used
        }
        metrics.timestamp = datetime.now(timezone.utc)
        
        # Store in history
        self._execution_history[task_name].append({
            'timestamp': datetime.now(timezone.utc),
            'success': success,
            'execution_time': execution_time,
            'memory_used': memory_used,
            'cpu_used': cpu_used
        })
        
        # Keep only last 100 entries
        if len(self._execution_history[task_name]) > 100:
            self._execution_history[task_name].popleft()
    
    def _check_task_health(self):
        """Check health of all background tasks"""
        current_time = datetime.now(timezone.utc)
        
        for task_name, metrics in self._task_health_metrics.items():
            # Check if task hasn't run recently
            time_since_last_run = (current_time - metrics.last_run).total_seconds()
            expected_interval = self.config.cache_cleanup_interval_minutes * 60 if 'cache' in task_name else self.config.database_cleanup_interval_hours * 3600
            
            if time_since_last_run > expected_interval * 2:  # Allow 2x the expected interval
                metrics.status = TaskHealthStatus.WARNING
                logger.warning(f"Task {task_name} hasn't run for {time_since_last_run:.0f} seconds")
    
    def _check_resource_usage(self):
        """Check system resource usage"""
        try:
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Log warnings for high resource usage
            if memory_percent > 90:
                logger.warning(f"High memory usage detected: {memory_percent:.1f}%")
            if cpu_percent > 90:
                logger.warning(f"High CPU usage detected: {cpu_percent:.1f}%")
                
        except Exception as e:
            logger.error(f"Failed to check resource usage: {sanitize_for_log(str(e))}")
    
    def _check_task_heartbeats(self):
        """Check task heartbeats for stuck tasks"""
        current_time = datetime.now(timezone.utc)
        
        for task_name, coord_info in self._task_coordination_info.items():
            if coord_info.is_running:
                time_since_heartbeat = (current_time - coord_info.last_heartbeat).total_seconds()
                
                if time_since_heartbeat > self._heartbeat_timeout:
                    logger.warning(f"Task {task_name} heartbeat timeout: {time_since_heartbeat:.0f} seconds")
                    
                    # Update health status
                    if task_name in self._task_health_metrics:
                        self._task_health_metrics[task_name].status = TaskHealthStatus.CRITICAL
                        self._task_health_metrics[task_name].last_error = f"Heartbeat timeout: {time_since_heartbeat:.0f}s"
    
    def _integrate_with_notification_monitor(self):
        """Integrate health metrics with notification system monitor"""
        try:
            # Update notification monitor with cleanup task health
            for task_name, metrics in self._task_health_metrics.items():
                # Add cleanup task metrics to notification monitor's error counts
                if metrics.status == TaskHealthStatus.CRITICAL:
                    self.notification_monitor._error_counts[f'cleanup_{task_name}_critical'] = 1
                elif metrics.status == TaskHealthStatus.WARNING:
                    self.notification_monitor._error_counts[f'cleanup_{task_name}_warning'] = 1
                else:
                    # Clear error counts for healthy tasks
                    self.notification_monitor._error_counts.pop(f'cleanup_{task_name}_critical', None)
                    self.notification_monitor._error_counts.pop(f'cleanup_{task_name}_warning', None)
            
            # Add overall cleanup system health
            critical_tasks = sum(1 for m in self._task_health_metrics.values() if m.status == TaskHealthStatus.CRITICAL)
            warning_tasks = sum(1 for m in self._task_health_metrics.values() if m.status == TaskHealthStatus.WARNING)
            
            if critical_tasks > 0:
                self.notification_monitor._error_counts['cleanup_system_critical'] = critical_tasks
            elif warning_tasks > 0:
                self.notification_monitor._error_counts['cleanup_system_warning'] = warning_tasks
            else:
                self.notification_monitor._error_counts.pop('cleanup_system_critical', None)
                self.notification_monitor._error_counts.pop('cleanup_system_warning', None)
                
        except Exception as e:
            logger.error(f"Failed to integrate with notification monitor: {sanitize_for_log(str(e))}")
    
    def _get_process_memory_usage(self) -> float:
        """Get current process memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0
    
    def monitor_task_health(self) -> Dict[str, Any]:
        """Get comprehensive task health monitoring data"""
        return {
            'task_health_metrics': {
                name: asdict(metrics) for name, metrics in self._task_health_metrics.items()
            },
            'task_coordination_info': {
                name: asdict(info) for name, info in self._task_coordination_info.items()
            },
            'running_tasks': list(self._running_tasks),
            'system_resources': {
                'memory_percent': psutil.virtual_memory().percent,
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'process_memory_mb': self._get_process_memory_usage()
            },
            'configuration': {
                'max_concurrent_tasks': self._max_concurrent_tasks,
                'health_check_interval': self._health_check_interval,
                'heartbeat_timeout': self._heartbeat_timeout
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def coordinate_cleanup_tasks(self) -> Dict[str, Any]:
        """Get task coordination status and control"""
        return {
            'coordination_status': {
                name: {
                    'can_run': self._can_run_task(name),
                    'is_running': name in self._running_tasks,
                    'dependencies': self._task_dependencies.get(name, []),
                    'resource_limits': info.resource_limits if name in self._task_coordination_info else {}
                }
                for name in self._cleanup_tasks.keys()
            },
            'resource_usage': {
                'current_memory_mb': self._get_process_memory_usage(),
                'current_cpu_percent': psutil.cpu_percent(interval=0.1),
                'running_task_count': len(self._running_tasks),
                'max_concurrent_tasks': self._max_concurrent_tasks
            },
            'execution_history': {
                name: list(history)[-10:]  # Last 10 executions
                for name, history in self._execution_history.items()
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
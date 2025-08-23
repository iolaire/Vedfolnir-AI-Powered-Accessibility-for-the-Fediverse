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
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from sqlalchemy import and_, func, text
from sqlalchemy.exc import SQLAlchemyError

from database import DatabaseManager
from models import JobAuditLog, CaptionGenerationTask, TaskStatus, ProcessingRun
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

@dataclass
class CleanupStats:
    """Statistics from cleanup operations"""
    operation_name: str
    items_cleaned: int
    execution_time_seconds: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

class BackgroundCleanupManager:
    """Manages background cleanup tasks for system maintenance"""
    
    def __init__(self, db_manager: DatabaseManager, redis_client: redis.Redis,
                 cache_manager: Optional[PerformanceCacheManager] = None,
                 config: Optional[CleanupConfig] = None):
        """
        Initialize background cleanup manager
        
        Args:
            db_manager: Database manager instance
            redis_client: Redis client for cache cleanup
            cache_manager: Optional cache manager instance
            config: Cleanup configuration
        """
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.cache_manager = cache_manager
        self.config = config or CleanupConfig()
        
        self._cleanup_stats = []
        self._cleanup_threads = {}
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()
        
        # Register cleanup tasks
        self._cleanup_tasks = {
            'audit_logs': self._cleanup_old_audit_logs,
            'failed_tasks': self._cleanup_old_failed_tasks,
            'completed_tasks': self._cleanup_old_completed_tasks,
            'cache_entries': self._cleanup_expired_cache_entries,
            'processing_runs': self._cleanup_old_processing_runs,
            'orphaned_data': self._cleanup_orphaned_data
        }
    
    def start_background_cleanup(self):
        """Start background cleanup threads"""
        if not self.config.cleanup_enabled:
            logger.info("Background cleanup is disabled")
            return
        
        logger.info("Starting background cleanup manager")
        
        # Start cache cleanup thread (runs more frequently)
        cache_thread = threading.Thread(
            target=self._run_periodic_cleanup,
            args=('cache_cleanup', self._cleanup_expired_cache_entries, 
                  self.config.cache_cleanup_interval_minutes * 60),
            daemon=True
        )
        cache_thread.start()
        self._cleanup_threads['cache_cleanup'] = cache_thread
        
        # Start database cleanup thread (runs less frequently)
        db_thread = threading.Thread(
            target=self._run_periodic_cleanup,
            args=('database_cleanup', self._run_all_database_cleanup,
                  self.config.database_cleanup_interval_hours * 3600),
            daemon=True
        )
        db_thread.start()
        self._cleanup_threads['database_cleanup'] = db_thread
        
        logger.info(f"Started {len(self._cleanup_threads)} background cleanup threads")
    
    def stop_background_cleanup(self):
        """Stop all background cleanup threads"""
        logger.info("Stopping background cleanup manager")
        self._shutdown_event.set()
        
        # Wait for threads to finish
        for thread_name, thread in self._cleanup_threads.items():
            if thread.is_alive():
                logger.info(f"Waiting for {thread_name} thread to finish...")
                thread.join(timeout=30)
                if thread.is_alive():
                    logger.warning(f"Thread {thread_name} did not finish gracefully")
        
        self._cleanup_threads.clear()
        logger.info("Background cleanup manager stopped")
    
    def _run_periodic_cleanup(self, task_name: str, cleanup_func: Callable, interval_seconds: int):
        """Run a cleanup function periodically"""
        logger.info(f"Started periodic cleanup task: {task_name} (interval: {interval_seconds}s)")
        
        while not self._shutdown_event.is_set():
            try:
                start_time = datetime.now()
                result = cleanup_func()
                execution_time = (datetime.now() - start_time).total_seconds()
                
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
                    logger.info(f"Cleanup task {task_name} completed: {result} items cleaned in {execution_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Error in cleanup task {task_name}: {sanitize_for_log(str(e))}")
                stats = CleanupStats(
                    operation_name=task_name,
                    items_cleaned=0,
                    execution_time_seconds=0,
                    timestamp=datetime.now(),
                    success=False,
                    error_message=str(e)
                )
                self._record_cleanup_stats(stats)
            
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
        Get cleanup statistics for the specified time period
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_stats = [s for s in self._cleanup_stats if s.timestamp >= cutoff_time]
        
        if not recent_stats:
            return {
                'message': f'No cleanup statistics available for the last {hours} hours',
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
            'config': {
                'cleanup_enabled': self.config.cleanup_enabled,
                'audit_log_retention_days': self.config.audit_log_retention_days,
                'metrics_retention_days': self.config.metrics_retention_days,
                'cache_cleanup_interval_minutes': self.config.cache_cleanup_interval_minutes,
                'database_cleanup_interval_hours': self.config.database_cleanup_interval_hours
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
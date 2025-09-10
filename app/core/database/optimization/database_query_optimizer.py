# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Database Query Optimizer for Multi-Tenant Caption Management

This module provides optimized database queries for admin operations,
including query caching, batch operations, and performance monitoring.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from sqlalchemy import text, func, and_, or_, desc, asc
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.core.database.core.database_manager import DatabaseManager
from models import (
    CaptionGenerationTask, TaskStatus, User, UserRole, PlatformConnection,
    JobPriority, SystemConfiguration, JobAuditLog, ProcessingRun
)
from app.services.performance.components.performance_cache_manager import PerformanceCacheManager, cached_method
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

@dataclass
class QueryPerformanceMetrics:
    """Query performance tracking metrics"""
    query_name: str
    execution_time_ms: float
    rows_returned: int
    cache_hit: bool
    timestamp: datetime

class DatabaseQueryOptimizer:
    """Optimized database queries for admin operations"""
    
    def __init__(self, db_manager: DatabaseManager, cache_manager: Optional[PerformanceCacheManager] = None):
        """
        Initialize database query optimizer
        
        Args:
            db_manager: Database manager instance
            cache_manager: Optional cache manager for query result caching
        """
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self._query_metrics = []
    
    def _track_query_performance(self, query_name: str, execution_time_ms: float, 
                               rows_returned: int, cache_hit: bool = False):
        """Track query performance metrics"""
        metric = QueryPerformanceMetrics(
            query_name=query_name,
            execution_time_ms=execution_time_ms,
            rows_returned=rows_returned,
            cache_hit=cache_hit,
            timestamp=datetime.now(timezone.utc)
        )
        self._query_metrics.append(metric)
        
        # Keep only last 1000 metrics
        if len(self._query_metrics) > 1000:
            self._query_metrics = self._query_metrics[-1000:]
    
    def get_admin_dashboard_data_optimized(self, admin_user_id: int) -> Dict[str, Any]:
        """
        Get optimized admin dashboard data with minimal database queries
        
        Args:
            admin_user_id: Admin user ID
            
        Returns:
            Dictionary with dashboard data
        """
        start_time = datetime.now()
        
        # Check cache first
        if self.cache_manager:
            cached_data = self.cache_manager.get_admin_dashboard_data(admin_user_id)
            if cached_data:
                self._track_query_performance(
                    'get_admin_dashboard_data_optimized', 
                    0, 
                    1, 
                    cache_hit=True
                )
                return cached_data
        
        with self.db_manager.get_session() as session:
            try:
                # Single query to get all task statistics
                task_stats_query = session.query(
                    CaptionGenerationTask.status,
                    func.count(CaptionGenerationTask.id).label('count')
                ).group_by(CaptionGenerationTask.status).all()
                
                # Convert to dictionary
                task_stats = {status.value: 0 for status in TaskStatus}
                for status, count in task_stats_query:
                    task_stats[status.value] = count
                
                # Single query to get user statistics
                user_stats = session.query(
                    func.count(User.id).label('total_users'),
                    func.sum(func.case((User.is_active == True, 1), else_=0)).label('active_users')
                ).first()
                
                # Single query to get recent errors (last 24 hours)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                recent_errors = session.query(CaptionGenerationTask).filter(
                    and_(
                        CaptionGenerationTask.status == TaskStatus.FAILED,
                        CaptionGenerationTask.completed_at >= cutoff_time
                    )
                ).options(
                    joinedload(CaptionGenerationTask.user),
                    joinedload(CaptionGenerationTask.platform_connection)
                ).order_by(desc(CaptionGenerationTask.completed_at)).limit(10).all()
                
                # Calculate performance metrics
                completed_tasks_24h = session.query(CaptionGenerationTask).filter(
                    and_(
                        CaptionGenerationTask.status == TaskStatus.COMPLETED,
                        CaptionGenerationTask.completed_at >= cutoff_time
                    )
                ).count()
                
                # Build dashboard data
                dashboard_data = {
                    'user_statistics': {
                        'total_users': user_stats.total_users or 0,
                        'active_users': user_stats.active_users or 0
                    },
                    'task_statistics': {
                        'total_tasks': sum(task_stats.values()),
                        'active_tasks': task_stats.get('queued', 0) + task_stats.get('running', 0),
                        'queued_tasks': task_stats.get('queued', 0),
                        'running_tasks': task_stats.get('running', 0),
                        'completed_tasks': task_stats.get('completed', 0),
                        'failed_tasks': task_stats.get('failed', 0),
                        'cancelled_tasks': task_stats.get('cancelled', 0)
                    },
                    'recent_errors': [
                        {
                            'task_id': task.id,
                            'user_id': task.user_id,
                            'username': task.user.username,
                            'platform_name': task.platform_connection.name,
                            'error_message': task.error_message,
                            'completed_at': task.completed_at.isoformat() if task.completed_at else None
                        }
                        for task in recent_errors
                    ],
                    'performance_metrics': {
                        'completed_tasks_24h': completed_tasks_24h,
                        'success_rate': self._calculate_success_rate(session, cutoff_time),
                        'avg_processing_time': self._calculate_avg_processing_time(session, cutoff_time)
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Cache the result
                if self.cache_manager:
                    self.cache_manager.cache_admin_dashboard_data(admin_user_id, dashboard_data)
                
                # Track performance
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self._track_query_performance(
                    'get_admin_dashboard_data_optimized',
                    execution_time,
                    len(dashboard_data)
                )
                
                return dashboard_data
                
            except SQLAlchemyError as e:
                logger.error(f"Database error in get_admin_dashboard_data_optimized: {sanitize_for_log(str(e))}")
                raise
    
    def get_user_jobs_optimized(self, user_id: int, limit: int = 50, 
                              status_filter: Optional[List[TaskStatus]] = None) -> List[Dict[str, Any]]:
        """
        Get optimized user job list with eager loading
        
        Args:
            user_id: User ID
            limit: Maximum number of jobs to return
            status_filter: Optional list of statuses to filter by
            
        Returns:
            List of job dictionaries
        """
        start_time = datetime.now()
        
        # Check cache first
        cache_key = f"user_jobs_{user_id}_{limit}_{status_filter}"
        if self.cache_manager:
            cached_data = self.cache_manager.get_cache(cache_key)
            if cached_data:
                self._track_query_performance(
                    'get_user_jobs_optimized',
                    0,
                    len(cached_data),
                    cache_hit=True
                )
                return cached_data
        
        with self.db_manager.get_session() as session:
            try:
                # Build query with eager loading
                query = session.query(CaptionGenerationTask).filter_by(user_id=user_id).options(
                    joinedload(CaptionGenerationTask.user),
                    joinedload(CaptionGenerationTask.platform_connection)
                )
                
                # Apply status filter if provided
                if status_filter:
                    query = query.filter(CaptionGenerationTask.status.in_(status_filter))
                
                # Order by creation date and limit
                jobs = query.order_by(desc(CaptionGenerationTask.created_at)).limit(limit).all()
                
                # Convert to dictionaries
                job_list = []
                for job in jobs:
                    job_dict = {
                        'task_id': job.id,
                        'status': job.status.value,
                        'priority': job.priority.value,
                        'created_at': job.created_at.isoformat(),
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'progress_percent': job.progress_percent,
                        'current_step': job.current_step,
                        'error_message': job.error_message,
                        'platform_name': job.platform_connection.name,
                        'retry_count': job.retry_count,
                        'max_retries': job.max_retries
                    }
                    job_list.append(job_dict)
                
                # Cache the result
                if self.cache_manager:
                    self.cache_manager.set_cache(cache_key, job_list, ttl=60)  # 1 minute TTL
                
                # Track performance
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self._track_query_performance(
                    'get_user_jobs_optimized',
                    execution_time,
                    len(job_list)
                )
                
                return job_list
                
            except SQLAlchemyError as e:
                logger.error(f"Database error in get_user_jobs_optimized: {sanitize_for_log(str(e))}")
                raise
    
    def get_system_metrics_optimized(self) -> Dict[str, Any]:
        """
        Get optimized system metrics with aggregated queries
        
        Returns:
            Dictionary with system metrics
        """
        start_time = datetime.now()
        
        # Check cache first
        if self.cache_manager:
            cached_data = self.cache_manager.get_system_metrics()
            if cached_data:
                self._track_query_performance(
                    'get_system_metrics_optimized',
                    0,
                    1,
                    cache_hit=True
                )
                return cached_data
        
        with self.db_manager.get_session() as session:
            try:
                # Single aggregated query for task metrics
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                
                task_metrics = session.query(
                    func.count(CaptionGenerationTask.id).label('total_tasks'),
                    func.sum(func.case(
                        (CaptionGenerationTask.status == TaskStatus.COMPLETED, 1),
                        else_=0
                    )).label('completed_tasks'),
                    func.sum(func.case(
                        (CaptionGenerationTask.status == TaskStatus.FAILED, 1),
                        else_=0
                    )).label('failed_tasks'),
                    func.sum(func.case(
                        (CaptionGenerationTask.status == TaskStatus.RUNNING, 1),
                        else_=0
                    )).label('running_tasks'),
                    func.sum(func.case(
                        (CaptionGenerationTask.status == TaskStatus.QUEUED, 1),
                        else_=0
                    )).label('queued_tasks'),
                    func.avg(func.case(
                        (and_(
                            CaptionGenerationTask.status == TaskStatus.COMPLETED,
                            CaptionGenerationTask.started_at.isnot(None),
                            CaptionGenerationTask.completed_at.isnot(None)
                        ), func.extract('epoch', CaptionGenerationTask.completed_at - CaptionGenerationTask.started_at))
                    )).label('avg_processing_time')
                ).filter(CaptionGenerationTask.created_at >= cutoff_time).first()
                
                # Get queue wait time estimate
                queue_wait_time = self._estimate_queue_wait_time(session)
                
                # Build metrics data
                metrics_data = {
                    'task_metrics': {
                        'total_tasks_24h': task_metrics.total_tasks or 0,
                        'completed_tasks_24h': task_metrics.completed_tasks or 0,
                        'failed_tasks_24h': task_metrics.failed_tasks or 0,
                        'running_tasks': task_metrics.running_tasks or 0,
                        'queued_tasks': task_metrics.queued_tasks or 0,
                        'avg_processing_time_seconds': float(task_metrics.avg_processing_time or 0),
                        'success_rate': self._calculate_success_rate_from_metrics(task_metrics),
                        'queue_wait_time_seconds': queue_wait_time
                    },
                    'system_health': {
                        'database_status': 'healthy',  # If we got here, DB is working
                        'active_connections': self._get_active_connections_count(session)
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Cache the result
                if self.cache_manager:
                    self.cache_manager.cache_system_metrics(metrics_data)
                
                # Track performance
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self._track_query_performance(
                    'get_system_metrics_optimized',
                    execution_time,
                    1
                )
                
                return metrics_data
                
            except SQLAlchemyError as e:
                logger.error(f"Database error in get_system_metrics_optimized: {sanitize_for_log(str(e))}")
                raise
    
    def batch_update_job_priorities(self, task_ids: List[str], priority: JobPriority, 
                                  admin_user_id: int) -> int:
        """
        Batch update job priorities for multiple tasks
        
        Args:
            task_ids: List of task IDs to update
            priority: New priority level
            admin_user_id: Admin user performing the update
            
        Returns:
            Number of tasks updated
        """
        start_time = datetime.now()
        
        with self.db_manager.get_session() as session:
            try:
                # Batch update query
                updated_count = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.id.in_(task_ids)
                ).update(
                    {
                        'priority': priority,
                        'updated_at': datetime.now(timezone.utc)
                    },
                    synchronize_session=False
                )
                
                # Log audit entries in batch
                audit_entries = []
                for task_id in task_ids:
                    audit_entries.append(JobAuditLog(
                        task_id=task_id,
                        admin_user_id=admin_user_id,
                        action='priority_updated',
                        details=f'priority={priority.value}',
                        timestamp=datetime.now(timezone.utc)
                    ))
                
                session.bulk_save_objects(audit_entries)
                session.commit()
                
                # Invalidate related caches
                if self.cache_manager:
                    for task_id in task_ids:
                        self.cache_manager.invalidate_job_caches(task_id)
                
                # Track performance
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self._track_query_performance(
                    'batch_update_job_priorities',
                    execution_time,
                    updated_count
                )
                
                logger.info(f"Batch updated {updated_count} job priorities by admin {admin_user_id}")
                return updated_count
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error in batch_update_job_priorities: {sanitize_for_log(str(e))}")
                raise
    
    def get_query_performance_stats(self) -> Dict[str, Any]:
        """
        Get query performance statistics
        
        Returns:
            Dictionary with performance statistics
        """
        if not self._query_metrics:
            return {'message': 'No query metrics available'}
        
        # Calculate statistics
        total_queries = len(self._query_metrics)
        cache_hits = sum(1 for m in self._query_metrics if m.cache_hit)
        avg_execution_time = sum(m.execution_time_ms for m in self._query_metrics) / total_queries
        
        # Group by query name
        query_stats = {}
        for metric in self._query_metrics:
            if metric.query_name not in query_stats:
                query_stats[metric.query_name] = {
                    'count': 0,
                    'total_time': 0,
                    'cache_hits': 0,
                    'avg_rows': 0
                }
            
            stats = query_stats[metric.query_name]
            stats['count'] += 1
            stats['total_time'] += metric.execution_time_ms
            stats['avg_rows'] += metric.rows_returned
            if metric.cache_hit:
                stats['cache_hits'] += 1
        
        # Calculate averages
        for query_name, stats in query_stats.items():
            stats['avg_time'] = stats['total_time'] / stats['count']
            stats['avg_rows'] = stats['avg_rows'] / stats['count']
            stats['cache_hit_rate'] = (stats['cache_hits'] / stats['count']) * 100
        
        return {
            'total_queries': total_queries,
            'cache_hit_rate': (cache_hits / total_queries) * 100,
            'avg_execution_time_ms': avg_execution_time,
            'query_breakdown': query_stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_success_rate(self, session: Session, cutoff_time: datetime) -> float:
        """Calculate success rate for tasks in the given time period"""
        try:
            total_completed = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.completed_at >= cutoff_time,
                    CaptionGenerationTask.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED])
                )
            ).count()
            
            if total_completed == 0:
                return 100.0
            
            successful = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.completed_at >= cutoff_time,
                    CaptionGenerationTask.status == TaskStatus.COMPLETED
                )
            ).count()
            
            return round((successful / total_completed) * 100, 2)
        except Exception:
            return 0.0
    
    def _calculate_avg_processing_time(self, session: Session, cutoff_time: datetime) -> float:
        """Calculate average processing time for completed tasks"""
        try:
            result = session.query(
                func.avg(func.extract('epoch', 
                    CaptionGenerationTask.completed_at - CaptionGenerationTask.started_at
                ))
            ).filter(
                and_(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at >= cutoff_time,
                    CaptionGenerationTask.started_at.isnot(None)
                )
            ).scalar()
            
            return float(result or 0)
        except Exception:
            return 0.0
    
    def _calculate_success_rate_from_metrics(self, task_metrics) -> float:
        """Calculate success rate from aggregated metrics"""
        completed = task_metrics.completed_tasks or 0
        failed = task_metrics.failed_tasks or 0
        total = completed + failed
        
        if total == 0:
            return 100.0
        
        return round((completed / total) * 100, 2)
    
    def _estimate_queue_wait_time(self, session: Session) -> float:
        """Estimate queue wait time based on current queue and processing rate"""
        try:
            # Get current queue size
            queued_count = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.QUEUED).count()
            
            if queued_count == 0:
                return 0.0
            
            # Get average processing time from recent completed tasks
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
            avg_processing_time = session.query(
                func.avg(func.extract('epoch',
                    CaptionGenerationTask.completed_at - CaptionGenerationTask.started_at
                ))
            ).filter(
                and_(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at >= cutoff_time,
                    CaptionGenerationTask.started_at.isnot(None)
                )
            ).scalar()
            
            if not avg_processing_time:
                return queued_count * 300  # Default 5 minutes per task
            
            return queued_count * float(avg_processing_time)
        except Exception:
            return 0.0
    
    def _get_active_connections_count(self, session: Session) -> int:
        """Get count of active database connections"""
        try:
            # This is MySQL-specific
            result = session.execute(text("SHOW STATUS LIKE 'Threads_connected'")).fetchone()
            return int(result[1]) if result else 0
        except Exception:
            return 0
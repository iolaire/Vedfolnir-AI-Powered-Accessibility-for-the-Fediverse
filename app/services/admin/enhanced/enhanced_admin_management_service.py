# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Admin Management Service with Performance Optimization

This service extends the existing AdminManagementService with caching,
optimized queries, and performance monitoring for improved response times.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict

from app.services.admin.components.admin_management_service import AdminManagementService, SystemOverview, JobDetails, ErrorDiagnostics
from app.core.database.core.database_manager import DatabaseManager
from app.services.task.core.task_queue_manager import TaskQueueManager
from app.services.performance.components.performance_cache_manager import PerformanceCacheManager, cached_method, CacheKeyGenerator
from app.core.database.optimization.database_query_optimizer import DatabaseQueryOptimizer
from app.services.task.core.background_cleanup_manager import BackgroundCleanupManager
from models import User, UserRole, CaptionGenerationTask, TaskStatus
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

@dataclass
class CachedSystemOverview(SystemOverview):
    """Extended system overview with cache metadata"""
    cache_hit: bool = False
    cache_timestamp: Optional[str] = None
    query_time_ms: float = 0.0

@dataclass
class PerformanceMetrics:
    """Performance metrics for admin operations"""
    cache_hit_rate: float
    avg_query_time_ms: float
    total_cached_operations: int
    cache_memory_usage_mb: float
    background_cleanup_stats: Dict[str, Any]

class EnhancedAdminManagementService(AdminManagementService):
    """Enhanced admin management service with caching and optimization"""
    
    def __init__(self, db_manager: DatabaseManager, task_queue_manager: TaskQueueManager,
                 cache_manager: PerformanceCacheManager, 
                 cleanup_manager: Optional[BackgroundCleanupManager] = None):
        """
        Initialize enhanced admin management service
        
        Args:
            db_manager: Database manager instance
            task_queue_manager: Task queue manager instance
            cache_manager: Performance cache manager for optimization
            cleanup_manager: Optional background cleanup manager
        """
        super().__init__(db_manager, task_queue_manager)
        self.cache_manager = cache_manager
        self.cleanup_manager = cleanup_manager
        self.query_optimizer = DatabaseQueryOptimizer(db_manager, cache_manager)
    
    def get_system_overview_cached(self, admin_user_id: int) -> CachedSystemOverview:
        """
        Get system overview with caching for improved performance
        
        Args:
            admin_user_id: Admin user ID requesting the overview
            
        Returns:
            CachedSystemOverview with performance metadata
        """
        start_time = datetime.now()
        
        # Check cache first
        cached_data = self.cache_manager.get_admin_dashboard_data(admin_user_id)
        if cached_data:
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Convert cached data to CachedSystemOverview
            overview = CachedSystemOverview(
                **cached_data,
                cache_hit=True,
                cache_timestamp=cached_data.get('timestamp'),
                query_time_ms=query_time
            )
            
            logger.debug(f"Admin dashboard cache hit for user {admin_user_id}")
            return overview
        
        # Get fresh data using optimized queries
        dashboard_data = self.query_optimizer.get_admin_dashboard_data_optimized(admin_user_id)
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Convert to CachedSystemOverview
        overview = CachedSystemOverview(
            total_users=dashboard_data['user_statistics']['total_users'],
            active_users=dashboard_data['user_statistics']['active_users'],
            total_tasks=dashboard_data['task_statistics']['total_tasks'],
            active_tasks=dashboard_data['task_statistics']['active_tasks'],
            queued_tasks=dashboard_data['task_statistics']['queued_tasks'],
            running_tasks=dashboard_data['task_statistics']['running_tasks'],
            completed_tasks=dashboard_data['task_statistics']['completed_tasks'],
            failed_tasks=dashboard_data['task_statistics']['failed_tasks'],
            cancelled_tasks=dashboard_data['task_statistics']['cancelled_tasks'],
            system_health_score=dashboard_data['performance_metrics'].get('success_rate', 100.0),
            resource_usage=self._get_resource_usage(),
            recent_errors=dashboard_data['recent_errors'],
            performance_metrics=dashboard_data['performance_metrics'],
            cache_hit=False,
            cache_timestamp=dashboard_data['timestamp'],
            query_time_ms=query_time
        )
        
        logger.debug(f"Admin dashboard fresh data for user {admin_user_id} (query time: {query_time:.2f}ms)")
        return overview
    
    def get_user_job_details_cached(self, admin_user_id: int, target_user_id: int, 
                                  limit: int = 50) -> List[JobDetails]:
        """
        Get user job details with caching
        
        Args:
            admin_user_id: Admin user ID requesting the details
            target_user_id: User ID whose jobs to inspect
            limit: Maximum number of jobs to return
            
        Returns:
            List of JobDetails objects
        """
        # Verify admin authorization first
        with self.db_manager.get_session() as session:
            self._verify_admin_authorization(session, admin_user_id)
            self._log_admin_action(session, admin_user_id, "get_user_job_details_cached", 
                                 details=f"target_user_id={target_user_id}")
            session.commit()
        
        # Use optimized query with caching
        job_data = self.query_optimizer.get_user_jobs_optimized(target_user_id, limit)
        
        # Convert to JobDetails objects
        job_details = []
        for job_dict in job_data:
            job_details.append(JobDetails(
                task_id=job_dict['task_id'],
                user_id=target_user_id,
                username='',  # Will be filled by the optimizer
                platform_name=job_dict['platform_name'],
                status=job_dict['status'],
                priority=job_dict['priority'],
                created_at=datetime.fromisoformat(job_dict['created_at']),
                started_at=datetime.fromisoformat(job_dict['started_at']) if job_dict['started_at'] else None,
                completed_at=datetime.fromisoformat(job_dict['completed_at']) if job_dict['completed_at'] else None,
                progress_percent=job_dict['progress_percent'],
                current_step=job_dict['current_step'],
                error_message=job_dict['error_message'],
                admin_notes=None,  # Not included in optimized query
                cancelled_by_admin=False,  # Not included in optimized query
                cancellation_reason=None,  # Not included in optimized query
                retry_count=job_dict['retry_count'],
                max_retries=job_dict['max_retries'],
                resource_usage=None  # Not included in optimized query
            ))
        
        return job_details
    
    def cancel_job_as_admin_with_cache_invalidation(self, admin_user_id: int, task_id: str, reason: str) -> bool:
        """
        Cancel job as admin and invalidate related caches
        
        Args:
            admin_user_id: Admin user ID performing the cancellation
            task_id: Task ID to cancel
            reason: Reason for cancellation
            
        Returns:
            bool: True if job was cancelled successfully
        """
        # Cancel the job using parent method
        success = super().cancel_job_as_admin(admin_user_id, task_id, reason)
        
        if success:
            # Invalidate related caches
            self.cache_manager.invalidate_job_caches(task_id)
            
            # Also invalidate admin dashboard cache for this admin
            admin_cache_key = CacheKeyGenerator.admin_dashboard(admin_user_id)
            self.cache_manager.delete_cache(admin_cache_key)
            
            logger.info(f"Invalidated caches after job cancellation: {task_id}")
        
        return success
    
    def get_cached_user_permissions(self, user_id: int) -> Dict[str, Any]:
        """
        Get user permissions with caching
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user permissions and role information
        """
        # Check cache first
        cached_permissions = self.cache_manager.get_user_permissions(user_id)
        if cached_permissions:
            return cached_permissions
        
        # Get fresh data from database
        with self.db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return {'error': 'User not found'}
            
            permissions_data = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'is_active': user.is_active,
                'is_admin': user.role == UserRole.ADMIN,
                'can_manage_users': user.role == UserRole.ADMIN,
                'can_view_all_jobs': user.role == UserRole.ADMIN,
                'can_cancel_jobs': user.role == UserRole.ADMIN,
                'can_modify_system_settings': user.role == UserRole.ADMIN,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Cache the permissions
            self.cache_manager.cache_user_permissions(user_id, permissions_data)
            
            return permissions_data
    
    def get_system_performance_metrics(self) -> PerformanceMetrics:
        """
        Get comprehensive system performance metrics
        
        Returns:
            PerformanceMetrics object with performance data
        """
        # Get cache statistics
        cache_stats = self.cache_manager.get_cache_stats()
        
        # Get query optimizer statistics
        query_stats = self.query_optimizer.get_query_performance_stats()
        
        # Get cleanup statistics if available
        cleanup_stats = {}
        if self.cleanup_manager:
            cleanup_stats = self.cleanup_manager.get_cleanup_stats(hours=24)
        
        return PerformanceMetrics(
            cache_hit_rate=cache_stats.get('cache_hit_rate', 0.0),
            avg_query_time_ms=query_stats.get('avg_execution_time_ms', 0.0),
            total_cached_operations=cache_stats.get('total_cache_keys', 0),
            cache_memory_usage_mb=self._parse_memory_usage(cache_stats.get('redis_memory_used', '0B')),
            background_cleanup_stats=cleanup_stats
        )
    
    def invalidate_user_related_caches(self, user_id: int) -> Dict[str, Any]:
        """
        Invalidate all caches related to a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with invalidation results
        """
        start_time = datetime.now()
        
        # Invalidate user-specific caches
        invalidated_count = self.cache_manager.invalidate_user_caches(user_id)
        
        # Also invalidate system-wide caches that might include this user's data
        system_patterns = [
            CacheKeyGenerator.system_metrics(),
            CacheKeyGenerator.queue_stats(),
            CacheKeyGenerator.performance_metrics()
        ]
        
        for pattern in system_patterns:
            self.cache_manager.delete_cache(pattern)
            invalidated_count += 1
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = {
            'user_id': user_id,
            'invalidated_cache_keys': invalidated_count,
            'execution_time_ms': execution_time,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Invalidated {invalidated_count} cache keys for user {user_id}")
        return result
    
    def run_manual_cleanup(self, cleanup_type: str, admin_user_id: int) -> Dict[str, Any]:
        """
        Run manual cleanup operation
        
        Args:
            cleanup_type: Type of cleanup to run
            admin_user_id: Admin user performing the cleanup
            
        Returns:
            Dictionary with cleanup results
        """
        # Verify admin authorization
        with self.db_manager.get_session() as session:
            self._verify_admin_authorization(session, admin_user_id)
            self._log_admin_action(session, admin_user_id, "run_manual_cleanup", 
                                 details=f"cleanup_type={cleanup_type}")
            session.commit()
        
        if not self.cleanup_manager:
            return {
                'success': False,
                'error': 'Background cleanup manager not available'
            }
        
        # Run the cleanup
        result = self.cleanup_manager.run_manual_cleanup(cleanup_type)
        
        # Add admin context to result
        result['admin_user_id'] = admin_user_id
        result['requested_at'] = datetime.now(timezone.utc).isoformat()
        
        return result
    
    def get_cache_performance_report(self, admin_user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive cache performance report
        
        Args:
            admin_user_id: Admin user requesting the report
            
        Returns:
            Dictionary with cache performance data
        """
        # Verify admin authorization
        with self.db_manager.get_session() as session:
            self._verify_admin_authorization(session, admin_user_id)
        
        # Get cache statistics
        cache_stats = self.cache_manager.get_cache_stats()
        
        # Get query optimizer statistics
        query_stats = self.query_optimizer.get_query_performance_stats()
        
        # Calculate cache efficiency metrics
        cache_hit_rate = cache_stats.get('cache_hit_rate', 0.0)
        memory_usage = cache_stats.get('redis_memory_used', '0B')
        
        # Determine performance rating
        performance_rating = self._calculate_performance_rating(cache_hit_rate, query_stats)
        
        return {
            'cache_statistics': cache_stats,
            'query_statistics': query_stats,
            'performance_rating': performance_rating,
            'recommendations': self._generate_performance_recommendations(cache_hit_rate, query_stats),
            'memory_usage': {
                'redis_memory': memory_usage,
                'cache_keys': cache_stats.get('total_cache_keys', 0)
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _parse_memory_usage(self, memory_str: str) -> float:
        """Parse Redis memory usage string to MB"""
        try:
            if memory_str.endswith('B'):
                return 0.0
            elif memory_str.endswith('K'):
                return float(memory_str[:-1]) / 1024
            elif memory_str.endswith('M'):
                return float(memory_str[:-1])
            elif memory_str.endswith('G'):
                return float(memory_str[:-1]) * 1024
            else:
                return 0.0
        except (ValueError, AttributeError):
            return 0.0
    
    def _calculate_performance_rating(self, cache_hit_rate: float, query_stats: Dict[str, Any]) -> str:
        """Calculate overall performance rating"""
        avg_query_time = query_stats.get('avg_execution_time_ms', 0)
        
        if cache_hit_rate >= 80 and avg_query_time <= 100:
            return 'excellent'
        elif cache_hit_rate >= 60 and avg_query_time <= 200:
            return 'good'
        elif cache_hit_rate >= 40 and avg_query_time <= 500:
            return 'fair'
        else:
            return 'poor'
    
    def _generate_performance_recommendations(self, cache_hit_rate: float, 
                                           query_stats: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        if cache_hit_rate < 50:
            recommendations.append("Consider increasing cache TTL values for frequently accessed data")
            recommendations.append("Review cache invalidation patterns to avoid premature cache eviction")
        
        avg_query_time = query_stats.get('avg_execution_time_ms', 0)
        if avg_query_time > 200:
            recommendations.append("Consider adding database indexes for slow queries")
            recommendations.append("Review query optimization opportunities")
        
        total_queries = query_stats.get('total_queries', 0)
        if total_queries > 1000:
            recommendations.append("High query volume detected - consider increasing cache retention")
        
        if not recommendations:
            recommendations.append("System performance is optimal")
        
        return recommendations
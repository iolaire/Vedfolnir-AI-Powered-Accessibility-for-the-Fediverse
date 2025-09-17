# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Health Checker

Provides comprehensive health checks for RQ system components,
including Redis connectivity, queue health, and worker status.
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Health check result data structure"""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    response_time: float = 0.0


class RQHealthChecker:
    """Comprehensive health checker for RQ system"""
    
    def __init__(self, db_manager: DatabaseManager, rq_queue_manager=None):
        """
        Initialize RQ health checker
        
        Args:
            db_manager: Database manager instance
            rq_queue_manager: RQ queue manager instance (optional)
        """
        self.db_manager = db_manager
        self.rq_queue_manager = rq_queue_manager
        
        # Health check timeouts
        self._redis_timeout = 5.0  # seconds
        self._database_timeout = 10.0  # seconds
        self._queue_timeout = 5.0  # seconds
    
    def check_overall_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of all RQ components
        
        Returns:
            Dict containing overall health status and component details
        """
        start_time = time.time()
        
        # Perform individual health checks
        checks = [
            self.check_redis_health(),
            self.check_database_health(),
            self.check_queue_health(),
            self.check_worker_health(),
            self.check_task_processing_health()
        ]
        
        # Determine overall status
        overall_status = self._determine_overall_status(checks)
        
        # Calculate total response time
        total_response_time = time.time() - start_time
        
        return {
            'status': overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'response_time': total_response_time,
            'components': {check.component: self._format_check_result(check) for check in checks},
            'summary': self._generate_health_summary(checks)
        }
    
    def check_redis_health(self) -> HealthCheckResult:
        """Check Redis connectivity and performance"""
        start_time = time.time()
        
        try:
            if not self.rq_queue_manager or not hasattr(self.rq_queue_manager, 'redis_connection'):
                return HealthCheckResult(
                    component='redis',
                    status=HealthStatus.ERROR,
                    message='RQ queue manager not available',
                    details={'error': 'RQ system not initialized'},
                    timestamp=datetime.now(timezone.utc),
                    response_time=time.time() - start_time
                )
            
            redis_conn = self.rq_queue_manager.redis_connection
            if not redis_conn:
                return HealthCheckResult(
                    component='redis',
                    status=HealthStatus.ERROR,
                    message='Redis connection not available',
                    details={'error': 'No Redis connection'},
                    timestamp=datetime.now(timezone.utc),
                    response_time=time.time() - start_time
                )
            
            # Test basic connectivity
            ping_start = time.time()
            redis_conn.ping()
            ping_time = time.time() - ping_start
            
            # Get Redis info
            redis_info = redis_conn.info()
            
            # Check memory usage
            used_memory = redis_info.get('used_memory', 0)
            max_memory = redis_info.get('maxmemory', 0)
            memory_usage_percent = 0
            if max_memory > 0:
                memory_usage_percent = (used_memory / max_memory) * 100
            
            # Determine status based on metrics
            if ping_time > 2.0:
                status = HealthStatus.WARNING
                message = f'Redis responding slowly (ping: {ping_time:.2f}s)'
            elif memory_usage_percent > 90:
                status = HealthStatus.WARNING
                message = f'High Redis memory usage ({memory_usage_percent:.1f}%)'
            else:
                status = HealthStatus.HEALTHY
                message = 'Redis is healthy'
            
            details = {
                'ping_time': ping_time,
                'memory_usage_bytes': used_memory,
                'memory_usage_percent': memory_usage_percent,
                'connected_clients': redis_info.get('connected_clients', 0),
                'uptime_seconds': redis_info.get('uptime_in_seconds', 0),
                'redis_version': redis_info.get('redis_version', 'unknown')
            }
            
            return HealthCheckResult(
                component='redis',
                status=status,
                message=message,
                details=details,
                timestamp=datetime.now(timezone.utc),
                response_time=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component='redis',
                status=HealthStatus.CRITICAL,
                message=f'Redis health check failed: {str(e)}',
                details={'error': str(e)},
                timestamp=datetime.now(timezone.utc),
                response_time=time.time() - start_time
            )
    
    def check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            session = self.db_manager.get_session()
            
            try:
                # Test basic connectivity with a simple query
                query_start = time.time()
                result = session.execute("SELECT 1").scalar()
                query_time = time.time() - query_start
                
                # Get task counts for health assessment
                total_tasks = session.query(CaptionGenerationTask).count()
                queued_tasks = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.QUEUED).count()
                running_tasks = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.RUNNING).count()
                
                # Check for stuck tasks
                stuck_threshold = datetime.now(timezone.utc) - timedelta(hours=2)
                stuck_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.RUNNING,
                    CaptionGenerationTask.started_at < stuck_threshold
                ).count()
                
                # Determine status
                if query_time > 5.0:
                    status = HealthStatus.WARNING
                    message = f'Database responding slowly (query: {query_time:.2f}s)'
                elif stuck_tasks > 0:
                    status = HealthStatus.WARNING
                    message = f'{stuck_tasks} tasks appear to be stuck'
                else:
                    status = HealthStatus.HEALTHY
                    message = 'Database is healthy'
                
                details = {
                    'query_time': query_time,
                    'total_tasks': total_tasks,
                    'queued_tasks': queued_tasks,
                    'running_tasks': running_tasks,
                    'stuck_tasks': stuck_tasks,
                    'connection_pool_size': getattr(self.db_manager, 'pool_size', 'unknown')
                }
                
                return HealthCheckResult(
                    component='database',
                    status=status,
                    message=message,
                    details=details,
                    timestamp=datetime.now(timezone.utc),
                    response_time=time.time() - start_time
                )
                
            finally:
                session.close()
                
        except Exception as e:
            return HealthCheckResult(
                component='database',
                status=HealthStatus.CRITICAL,
                message=f'Database health check failed: {str(e)}',
                details={'error': str(e)},
                timestamp=datetime.now(timezone.utc),
                response_time=time.time() - start_time
            )
    
    def check_queue_health(self) -> HealthCheckResult:
        """Check RQ queue health and statistics"""
        start_time = time.time()
        
        try:
            if not self.rq_queue_manager:
                return HealthCheckResult(
                    component='queues',
                    status=HealthStatus.ERROR,
                    message='RQ queue manager not available',
                    details={'error': 'RQ system not initialized'},
                    timestamp=datetime.now(timezone.utc),
                    response_time=time.time() - start_time
                )
            
            # Get queue statistics
            queue_stats = self.rq_queue_manager.get_queue_stats()
            
            # Analyze queue health
            total_pending = queue_stats.get('total_pending', 0)
            total_failed = queue_stats.get('total_failed', 0)
            redis_available = queue_stats.get('redis_available', False)
            fallback_mode = queue_stats.get('fallback_mode', False)
            
            # Determine status
            if not redis_available:
                status = HealthStatus.ERROR
                message = 'Redis unavailable - using database fallback'
            elif fallback_mode:
                status = HealthStatus.WARNING
                message = 'Operating in fallback mode'
            elif total_pending > 100:
                status = HealthStatus.WARNING
                message = f'High queue backlog ({total_pending} pending tasks)'
            elif total_failed > 50:
                status = HealthStatus.WARNING
                message = f'High failure rate ({total_failed} failed tasks)'
            else:
                status = HealthStatus.HEALTHY
                message = 'Queues are healthy'
            
            details = {
                'redis_available': redis_available,
                'fallback_mode': fallback_mode,
                'total_pending': total_pending,
                'total_failed': total_failed,
                'queue_stats': queue_stats.get('queues', {})
            }
            
            return HealthCheckResult(
                component='queues',
                status=status,
                message=message,
                details=details,
                timestamp=datetime.now(timezone.utc),
                response_time=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component='queues',
                status=HealthStatus.CRITICAL,
                message=f'Queue health check failed: {str(e)}',
                details={'error': str(e)},
                timestamp=datetime.now(timezone.utc),
                response_time=time.time() - start_time
            )
    
    def check_worker_health(self) -> HealthCheckResult:
        """Check RQ worker health and status"""
        start_time = time.time()
        
        try:
            # Note: This is a placeholder implementation
            # Full worker health checking would require integration with RQ worker manager
            
            if not self.rq_queue_manager:
                return HealthCheckResult(
                    component='workers',
                    status=HealthStatus.ERROR,
                    message='RQ queue manager not available',
                    details={'error': 'RQ system not initialized'},
                    timestamp=datetime.now(timezone.utc),
                    response_time=time.time() - start_time
                )
            
            # Check if RQ system is initialized
            health_status = self.rq_queue_manager.get_health_status()
            
            # Basic worker health assessment
            if not health_status.get('redis_available', False):
                status = HealthStatus.ERROR
                message = 'Workers cannot operate without Redis'
            elif health_status.get('fallback_mode', False):
                status = HealthStatus.WARNING
                message = 'Workers operating in fallback mode'
            else:
                status = HealthStatus.HEALTHY
                message = 'Worker system appears healthy'
            
            details = {
                'worker_manager_available': False,  # Would be True when worker manager is implemented
                'active_workers': 0,  # Would be actual count when implemented
                'worker_utilization': 0.0,  # Would be actual utilization when implemented
                'health_status': health_status
            }
            
            return HealthCheckResult(
                component='workers',
                status=status,
                message=message,
                details=details,
                timestamp=datetime.now(timezone.utc),
                response_time=time.time() - start_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component='workers',
                status=HealthStatus.CRITICAL,
                message=f'Worker health check failed: {str(e)}',
                details={'error': str(e)},
                timestamp=datetime.now(timezone.utc),
                response_time=time.time() - start_time
            )
    
    def check_task_processing_health(self) -> HealthCheckResult:
        """Check task processing health and performance"""
        start_time = time.time()
        
        try:
            session = self.db_manager.get_session()
            
            try:
                # Calculate processing metrics for the last hour
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                
                completed_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at >= one_hour_ago
                ).count()
                
                failed_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.FAILED,
                    CaptionGenerationTask.completed_at >= one_hour_ago
                ).count()
                
                # Calculate success rate
                total_processed = completed_tasks + failed_tasks
                success_rate = (completed_tasks / total_processed * 100) if total_processed > 0 else 100
                
                # Check processing times
                recent_completed = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at >= one_hour_ago,
                    CaptionGenerationTask.started_at.isnot(None)
                ).all()
                
                processing_times = []
                for task in recent_completed:
                    if task.started_at and task.completed_at:
                        duration = (task.completed_at - task.started_at).total_seconds()
                        processing_times.append(duration)
                
                avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
                
                # Determine status
                if success_rate < 70:
                    status = HealthStatus.CRITICAL
                    message = f'Critical success rate: {success_rate:.1f}%'
                elif success_rate < 85:
                    status = HealthStatus.WARNING
                    message = f'Low success rate: {success_rate:.1f}%'
                elif avg_processing_time > 600:  # 10 minutes
                    status = HealthStatus.WARNING
                    message = f'Slow processing: {avg_processing_time:.1f}s average'
                else:
                    status = HealthStatus.HEALTHY
                    message = 'Task processing is healthy'
                
                details = {
                    'completed_tasks_1h': completed_tasks,
                    'failed_tasks_1h': failed_tasks,
                    'success_rate': success_rate,
                    'avg_processing_time': avg_processing_time,
                    'processing_samples': len(processing_times)
                }
                
                return HealthCheckResult(
                    component='task_processing',
                    status=status,
                    message=message,
                    details=details,
                    timestamp=datetime.now(timezone.utc),
                    response_time=time.time() - start_time
                )
                
            finally:
                session.close()
                
        except Exception as e:
            return HealthCheckResult(
                component='task_processing',
                status=HealthStatus.CRITICAL,
                message=f'Task processing health check failed: {str(e)}',
                details={'error': str(e)},
                timestamp=datetime.now(timezone.utc),
                response_time=time.time() - start_time
            )
    
    def _determine_overall_status(self, checks: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall health status from individual checks"""
        if any(check.status == HealthStatus.CRITICAL for check in checks):
            return HealthStatus.CRITICAL
        elif any(check.status == HealthStatus.ERROR for check in checks):
            return HealthStatus.ERROR
        elif any(check.status == HealthStatus.WARNING for check in checks):
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _format_check_result(self, check: HealthCheckResult) -> Dict[str, Any]:
        """Format a health check result for API response"""
        return {
            'status': check.status.value,
            'message': check.message,
            'details': check.details,
            'timestamp': check.timestamp.isoformat(),
            'response_time': check.response_time
        }
    
    def _generate_health_summary(self, checks: List[HealthCheckResult]) -> Dict[str, Any]:
        """Generate a summary of health check results"""
        status_counts = {}
        for status in HealthStatus:
            status_counts[status.value] = sum(1 for check in checks if check.status == status)
        
        total_response_time = sum(check.response_time for check in checks)
        
        return {
            'total_checks': len(checks),
            'status_distribution': status_counts,
            'total_response_time': total_response_time,
            'issues': [
                {
                    'component': check.component,
                    'status': check.status.value,
                    'message': check.message
                }
                for check in checks 
                if check.status in [HealthStatus.WARNING, HealthStatus.ERROR, HealthStatus.CRITICAL]
            ]
        }
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
System Monitor for Multi-Tenant Caption Management

This module provides comprehensive system monitoring capabilities including:
- Real-time system health monitoring
- Performance metrics collection
- Stuck job detection
- Error trend analysis
- Queue wait time prediction
- Redis-based metrics storage
"""

import logging
import json
import redis
import psutil
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from database import DatabaseManager
from models import (
    CaptionGenerationTask, TaskStatus, User, UserRole, 
    ProcessingRun, AlertType, AlertSeverity
)
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

@dataclass
class SystemHealth:
    """System health status data structure"""
    status: str  # 'healthy', 'warning', 'critical'
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    database_status: str
    redis_status: str
    active_tasks: int
    queued_tasks: int
    failed_tasks_last_hour: int
    avg_processing_time: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    job_completion_rate: float  # jobs per hour
    avg_processing_time: float  # seconds
    success_rate: float  # percentage
    error_rate: float  # percentage
    queue_wait_time: float  # average seconds
    resource_usage: Dict[str, float]  # CPU, memory, disk
    throughput_metrics: Dict[str, int]  # various counts
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class ErrorTrends:
    """Error trend analysis data structure"""
    total_errors: int
    error_rate: float
    error_categories: Dict[str, int]
    trending_errors: List[Dict[str, Any]]
    error_patterns: List[Dict[str, Any]]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class ResourceUsage:
    """Resource usage data structure"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_io: Dict[str, int]
    database_connections: int
    redis_memory_mb: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class SystemMonitor:
    """System monitor for real-time health monitoring and metrics collection"""
    
    def __init__(self, db_manager: DatabaseManager, redis_client: Optional[redis.Redis] = None,
                 stuck_job_timeout: int = 3600, metrics_retention_hours: int = 168):
        """
        Initialize system monitor
        
        Args:
            db_manager: Database manager instance
            redis_client: Redis client for metrics storage
            stuck_job_timeout: Timeout in seconds for stuck job detection
            metrics_retention_hours: How long to retain metrics (default: 7 days)
        """
        self.db_manager = db_manager
        self.stuck_job_timeout = stuck_job_timeout
        self.metrics_retention_hours = metrics_retention_hours
        
        # Initialize Redis client for metrics storage
        if redis_client:
            self.redis_client = redis_client
        else:
            try:
                # Create Redis client with default settings
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=1,  # Use different DB for metrics
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for metrics storage: {e}")
                self.redis_client = None
        
        # Metrics storage keys
        self.metrics_prefix = "vedfolnir:metrics:"
        self.health_key = f"{self.metrics_prefix}health"
        self.performance_key = f"{self.metrics_prefix}performance"
        self.errors_key = f"{self.metrics_prefix}errors"
        self.resources_key = f"{self.metrics_prefix}resources"
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Error tracking for trend analysis
        self._error_history = deque(maxlen=1000)  # Keep last 1000 errors
        self._error_categories = defaultdict(int)
        
        logger.info("System monitor initialized")
    
    def get_system_health(self) -> SystemHealth:
        """
        Get current system health status
        
        Returns:
            SystemHealth object with current status
        """
        try:
            # Get system resource usage
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get database status
            database_status = self._check_database_status()
            
            # Get Redis status
            redis_status = self._check_redis_status()
            
            # Get task statistics
            task_stats = self._get_task_statistics()
            
            # Get processing time statistics
            avg_processing_time = self._get_average_processing_time()
            
            # Determine overall health status
            health_status = self._determine_health_status(
                cpu_usage, memory.percent, disk.percent,
                database_status, redis_status, task_stats
            )
            
            health = SystemHealth(
                status=health_status,
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                database_status=database_status,
                redis_status=redis_status,
                active_tasks=task_stats.get('running', 0),
                queued_tasks=task_stats.get('queued', 0),
                failed_tasks_last_hour=task_stats.get('failed_last_hour', 0),
                avg_processing_time=avg_processing_time,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Store in Redis for historical tracking
            self._store_health_metrics(health)
            
            return health
            
        except Exception as e:
            logger.error(f"Error getting system health: {sanitize_for_log(str(e))}")
            # Return minimal health status on error
            return SystemHealth(
                status='critical',
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                database_status='error',
                redis_status='error',
                active_tasks=0,
                queued_tasks=0,
                failed_tasks_last_hour=0,
                avg_processing_time=0.0,
                timestamp=datetime.now(timezone.utc)
            )
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """
        Get current performance metrics
        
        Returns:
            PerformanceMetrics object with current metrics
        """
        try:
            # Calculate job completion rate (jobs per hour)
            completion_rate = self._calculate_completion_rate()
            
            # Get average processing time
            avg_processing_time = self._get_average_processing_time()
            
            # Calculate success and error rates
            success_rate, error_rate = self._calculate_success_error_rates()
            
            # Get queue wait time
            queue_wait_time = self._calculate_queue_wait_time()
            
            # Get resource usage
            resource_usage = self._get_resource_usage_dict()
            
            # Get throughput metrics
            throughput_metrics = self._get_throughput_metrics()
            
            metrics = PerformanceMetrics(
                job_completion_rate=completion_rate,
                avg_processing_time=avg_processing_time,
                success_rate=success_rate,
                error_rate=error_rate,
                queue_wait_time=queue_wait_time,
                resource_usage=resource_usage,
                throughput_metrics=throughput_metrics,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Store in Redis for historical tracking
            self._store_performance_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {sanitize_for_log(str(e))}")
            # Return minimal metrics on error
            return PerformanceMetrics(
                job_completion_rate=0.0,
                avg_processing_time=0.0,
                success_rate=0.0,
                error_rate=100.0,
                queue_wait_time=0.0,
                resource_usage={},
                throughput_metrics={},
                timestamp=datetime.now(timezone.utc)
            )
    
    def check_resource_usage(self) -> ResourceUsage:
        """
        Get detailed resource usage information
        
        Returns:
            ResourceUsage object with detailed resource metrics
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_used_mb = memory.used / (1024 * 1024)
            memory_total_mb = memory.total / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_total_gb = disk.total / (1024 * 1024 * 1024)
            
            # Network I/O
            network_io = psutil.net_io_counters()._asdict()
            
            # Database connections
            database_connections = self._get_database_connection_count()
            
            # Redis memory usage
            redis_memory_mb = self._get_redis_memory_usage()
            
            usage = ResourceUsage(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory_used_mb,
                memory_total_mb=memory_total_mb,
                disk_percent=disk.percent,
                disk_used_gb=disk_used_gb,
                disk_total_gb=disk_total_gb,
                network_io=network_io,
                database_connections=database_connections,
                redis_memory_mb=redis_memory_mb,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Store in Redis for historical tracking
            self._store_resource_metrics(usage)
            
            return usage
            
        except Exception as e:
            logger.error(f"Error checking resource usage: {sanitize_for_log(str(e))}")
            # Return minimal usage on error
            return ResourceUsage(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_total_mb=0.0,
                disk_percent=0.0,
                disk_used_gb=0.0,
                disk_total_gb=0.0,
                network_io={},
                database_connections=0,
                redis_memory_mb=0.0,
                timestamp=datetime.now(timezone.utc)
            )
    
    def detect_stuck_jobs(self) -> List[str]:
        """
        Detect jobs that have been running longer than the timeout threshold
        
        Returns:
            List of task IDs that appear to be stuck
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.stuck_job_timeout)
            
            session = self.db_manager.get_session()
            try:
                # Find running tasks that started before the cutoff time
                stuck_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.RUNNING,
                    CaptionGenerationTask.started_at < cutoff_time
                ).all()
                
                stuck_task_ids = [task.id for task in stuck_tasks]
                
                if stuck_task_ids:
                    logger.warning(f"Detected {len(stuck_task_ids)} stuck jobs: {stuck_task_ids}")
                
                return stuck_task_ids
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error detecting stuck jobs: {sanitize_for_log(str(e))}")
            return []
    
    def get_error_trends(self, hours: int = 24) -> ErrorTrends:
        """
        Analyze error trends over the specified time period
        
        Args:
            hours: Number of hours to analyze (default: 24)
            
        Returns:
            ErrorTrends object with error analysis
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            session = self.db_manager.get_session()
            try:
                # Get failed tasks in the time period
                failed_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.FAILED,
                    CaptionGenerationTask.completed_at >= cutoff_time
                ).all()
                
                # Get total tasks for error rate calculation
                total_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.created_at >= cutoff_time
                ).count()
                
                # Analyze error patterns
                error_categories = defaultdict(int)
                trending_errors = []
                
                for task in failed_tasks:
                    if task.error_message:
                        # Categorize errors based on message content
                        category = self._categorize_error(task.error_message)
                        error_categories[category] += 1
                        
                        trending_errors.append({
                            'task_id': task.id,
                            'error_message': task.error_message,
                            'category': category,
                            'timestamp': task.completed_at.isoformat() if task.completed_at else None,
                            'user_id': task.user_id
                        })
                
                # Calculate error rate
                error_rate = (len(failed_tasks) / max(total_tasks, 1)) * 100
                
                # Identify error patterns
                error_patterns = self._identify_error_patterns(trending_errors)
                
                trends = ErrorTrends(
                    total_errors=len(failed_tasks),
                    error_rate=error_rate,
                    error_categories=dict(error_categories),
                    trending_errors=trending_errors[-10:],  # Last 10 errors
                    error_patterns=error_patterns,
                    timestamp=datetime.now(timezone.utc)
                )
                
                # Store in Redis for historical tracking
                self._store_error_trends(trends)
                
                return trends
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error analyzing error trends: {sanitize_for_log(str(e))}")
            return ErrorTrends(
                total_errors=0,
                error_rate=0.0,
                error_categories={},
                trending_errors=[],
                error_patterns=[],
                timestamp=datetime.now(timezone.utc)
            )
    
    def predict_queue_wait_time(self) -> int:
        """
        Predict queue wait time based on current system load
        
        Returns:
            Estimated wait time in seconds
        """
        try:
            session = self.db_manager.get_session()
            try:
                # Get current queue statistics
                queued_count = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.QUEUED
                ).count()
                
                running_count = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.RUNNING
                ).count()
                
                # Get average processing time from recent completed tasks
                avg_processing_time = self._get_average_processing_time()
                
                # Estimate concurrent processing capacity (assume max 3 concurrent tasks)
                max_concurrent = 3
                current_capacity = max_concurrent - running_count
                
                if current_capacity <= 0:
                    # No capacity, wait for current tasks to complete
                    estimated_wait = avg_processing_time
                else:
                    # Calculate wait time based on queue position and processing rate
                    processing_rate = current_capacity / max(avg_processing_time, 1)  # tasks per second
                    estimated_wait = queued_count / max(processing_rate, 0.001)  # avoid division by zero
                
                # Add some buffer for system overhead
                estimated_wait = int(estimated_wait * 1.2)
                
                logger.debug(f"Queue wait time prediction: {estimated_wait}s (queued: {queued_count}, running: {running_count})")
                
                return estimated_wait
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error predicting queue wait time: {sanitize_for_log(str(e))}")
            return 300  # Default to 5 minutes on error
    
    def _check_database_status(self) -> str:
        """Check database connectivity and status"""
        try:
            session = self.db_manager.get_session()
            try:
                # Simple query to test database connectivity
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
                return 'healthy'
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Database health check failed: {sanitize_for_log(str(e))}")
            return 'error'
    
    def _check_redis_status(self) -> str:
        """Check Redis connectivity and status"""
        try:
            if self.redis_client:
                self.redis_client.ping()
                return 'healthy'
            else:
                return 'unavailable'
        except Exception as e:
            logger.error(f"Redis health check failed: {sanitize_for_log(str(e))}")
            return 'error'
    
    def _get_task_statistics(self) -> Dict[str, int]:
        """Get current task statistics"""
        try:
            session = self.db_manager.get_session()
            try:
                stats = {}
                
                # Count tasks by status
                for status in TaskStatus:
                    count = session.query(CaptionGenerationTask).filter(
                        CaptionGenerationTask.status == status
                    ).count()
                    stats[status.value] = count
                
                # Count failed tasks in the last hour
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                failed_last_hour = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.FAILED,
                    CaptionGenerationTask.completed_at >= one_hour_ago
                ).count()
                stats['failed_last_hour'] = failed_last_hour
                
                return stats
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting task statistics: {sanitize_for_log(str(e))}")
            return {}
    
    def _get_average_processing_time(self) -> float:
        """Get average processing time for completed tasks"""
        try:
            session = self.db_manager.get_session()
            try:
                # Get completed tasks from the last 24 hours
                one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
                
                completed_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at >= one_day_ago,
                    CaptionGenerationTask.started_at.isnot(None),
                    CaptionGenerationTask.completed_at.isnot(None)
                ).all()
                
                if not completed_tasks:
                    return 300.0  # Default 5 minutes if no data
                
                # Calculate average processing time
                total_time = 0
                for task in completed_tasks:
                    if task.started_at and task.completed_at:
                        processing_time = (task.completed_at - task.started_at).total_seconds()
                        total_time += processing_time
                
                avg_time = total_time / len(completed_tasks)
                return avg_time
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error calculating average processing time: {sanitize_for_log(str(e))}")
            return 300.0  # Default 5 minutes on error
    
    def _determine_health_status(self, cpu_usage: float, memory_usage: float, 
                                disk_usage: float, database_status: str, 
                                redis_status: str, task_stats: Dict[str, int]) -> str:
        """Determine overall system health status"""
        # Check for critical conditions
        if (cpu_usage > 90 or memory_usage > 90 or disk_usage > 95 or 
            database_status == 'error'):
            return 'critical'
        
        # Check for warning conditions
        if (cpu_usage > 70 or memory_usage > 70 or disk_usage > 80 or 
            redis_status == 'error' or task_stats.get('failed_last_hour', 0) > 10):
            return 'warning'
        
        return 'healthy'
    
    def _calculate_completion_rate(self) -> float:
        """Calculate job completion rate (jobs per hour)"""
        try:
            session = self.db_manager.get_session()
            try:
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                
                completed_count = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at >= one_hour_ago
                ).count()
                
                return float(completed_count)
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error calculating completion rate: {sanitize_for_log(str(e))}")
            return 0.0
    
    def _calculate_success_error_rates(self) -> Tuple[float, float]:
        """Calculate success and error rates"""
        try:
            session = self.db_manager.get_session()
            try:
                one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
                
                total_completed = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED]),
                    CaptionGenerationTask.completed_at >= one_day_ago
                ).count()
                
                successful = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at >= one_day_ago
                ).count()
                
                if total_completed == 0:
                    return 100.0, 0.0  # No data, assume perfect
                
                success_rate = (successful / total_completed) * 100
                error_rate = 100 - success_rate
                
                return success_rate, error_rate
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error calculating success/error rates: {sanitize_for_log(str(e))}")
            return 0.0, 100.0
    
    def _calculate_queue_wait_time(self) -> float:
        """Calculate average queue wait time"""
        try:
            session = self.db_manager.get_session()
            try:
                # Get recently started tasks
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                
                started_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.started_at >= one_hour_ago,
                    CaptionGenerationTask.created_at.isnot(None),
                    CaptionGenerationTask.started_at.isnot(None)
                ).all()
                
                if not started_tasks:
                    return 0.0
                
                total_wait_time = 0
                for task in started_tasks:
                    if task.created_at and task.started_at:
                        wait_time = (task.started_at - task.created_at).total_seconds()
                        total_wait_time += wait_time
                
                avg_wait_time = total_wait_time / len(started_tasks)
                return avg_wait_time
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error calculating queue wait time: {sanitize_for_log(str(e))}")
            return 0.0
    
    def _get_resource_usage_dict(self) -> Dict[str, float]:
        """Get resource usage as dictionary"""
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_usage,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent
            }
        except Exception as e:
            logger.error(f"Error getting resource usage: {sanitize_for_log(str(e))}")
            return {}
    
    def _get_throughput_metrics(self) -> Dict[str, int]:
        """Get throughput metrics"""
        try:
            session = self.db_manager.get_session()
            try:
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                
                metrics = {
                    'tasks_created_last_hour': session.query(CaptionGenerationTask).filter(
                        CaptionGenerationTask.created_at >= one_hour_ago
                    ).count(),
                    'tasks_completed_last_hour': session.query(CaptionGenerationTask).filter(
                        CaptionGenerationTask.status == TaskStatus.COMPLETED,
                        CaptionGenerationTask.completed_at >= one_hour_ago
                    ).count(),
                    'tasks_failed_last_hour': session.query(CaptionGenerationTask).filter(
                        CaptionGenerationTask.status == TaskStatus.FAILED,
                        CaptionGenerationTask.completed_at >= one_hour_ago
                    ).count()
                }
                
                return metrics
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting throughput metrics: {sanitize_for_log(str(e))}")
            return {}
    
    def _get_database_connection_count(self) -> int:
        """Get current database connection count"""
        try:
            # This would need to be implemented based on the specific database
            # For now, return a placeholder
            return 0
        except Exception:
            return 0
    
    def _get_redis_memory_usage(self) -> float:
        """Get Redis memory usage in MB"""
        try:
            if self.redis_client:
                info = self.redis_client.info('memory')
                used_memory = info.get('used_memory', 0)
                return used_memory / (1024 * 1024)  # Convert to MB
            return 0.0
        except Exception:
            return 0.0
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error based on message content"""
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower or 'timed out' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower or 'network' in error_lower:
            return 'network'
        elif 'authentication' in error_lower or 'unauthorized' in error_lower:
            return 'authentication'
        elif 'rate limit' in error_lower or 'too many requests' in error_lower:
            return 'rate_limit'
        elif 'database' in error_lower or 'sql' in error_lower:
            return 'database'
        elif 'redis' in error_lower:
            return 'redis'
        elif 'ollama' in error_lower or 'llava' in error_lower:
            return 'ai_service'
        elif 'permission' in error_lower or 'forbidden' in error_lower:
            return 'permission'
        else:
            return 'other'
    
    def _identify_error_patterns(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify patterns in error occurrences"""
        patterns = []
        
        # Group errors by category and time
        category_counts = defaultdict(int)
        for error in errors:
            category_counts[error['category']] += 1
        
        # Identify high-frequency error categories
        for category, count in category_counts.items():
            if count >= 3:  # Pattern threshold
                patterns.append({
                    'type': 'high_frequency',
                    'category': category,
                    'count': count,
                    'description': f"High frequency of {category} errors: {count} occurrences"
                })
        
        return patterns
    
    def _store_health_metrics(self, health: SystemHealth):
        """Store health metrics in Redis"""
        if not self.redis_client:
            return
        
        try:
            # Store current health
            self.redis_client.hset(
                self.health_key,
                mapping=health.to_dict()
            )
            
            # Store in time series for historical data
            timestamp_key = f"{self.health_key}:history:{int(health.timestamp.timestamp())}"
            self.redis_client.setex(
                timestamp_key,
                timedelta(hours=self.metrics_retention_hours),
                json.dumps(health.to_dict())
            )
            
        except Exception as e:
            logger.error(f"Error storing health metrics: {sanitize_for_log(str(e))}")
    
    def _store_performance_metrics(self, metrics: PerformanceMetrics):
        """Store performance metrics in Redis"""
        if not self.redis_client:
            return
        
        try:
            # Store current metrics
            self.redis_client.hset(
                self.performance_key,
                mapping=metrics.to_dict()
            )
            
            # Store in time series for historical data
            timestamp_key = f"{self.performance_key}:history:{int(metrics.timestamp.timestamp())}"
            self.redis_client.setex(
                timestamp_key,
                timedelta(hours=self.metrics_retention_hours),
                json.dumps(metrics.to_dict())
            )
            
        except Exception as e:
            logger.error(f"Error storing performance metrics: {sanitize_for_log(str(e))}")
    
    def _store_error_trends(self, trends: ErrorTrends):
        """Store error trends in Redis"""
        if not self.redis_client:
            return
        
        try:
            # Store current trends
            self.redis_client.hset(
                self.errors_key,
                mapping=trends.to_dict()
            )
            
            # Store in time series for historical data
            timestamp_key = f"{self.errors_key}:history:{int(trends.timestamp.timestamp())}"
            self.redis_client.setex(
                timestamp_key,
                timedelta(hours=self.metrics_retention_hours),
                json.dumps(trends.to_dict())
            )
            
        except Exception as e:
            logger.error(f"Error storing error trends: {sanitize_for_log(str(e))}")
    
    def _store_resource_metrics(self, usage: ResourceUsage):
        """Store resource metrics in Redis"""
        if not self.redis_client:
            return
        
        try:
            # Store current usage
            self.redis_client.hset(
                self.resources_key,
                mapping=usage.to_dict()
            )
            
            # Store in time series for historical data
            timestamp_key = f"{self.resources_key}:history:{int(usage.timestamp.timestamp())}"
            self.redis_client.setex(
                timestamp_key,
                timedelta(hours=self.metrics_retention_hours),
                json.dumps(usage.to_dict())
            )
            
        except Exception as e:
            logger.error(f"Error storing resource metrics: {sanitize_for_log(str(e))}")
    
    def get_historical_metrics(self, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get historical metrics from Redis
        
        Args:
            metric_type: Type of metrics ('health', 'performance', 'errors', 'resources')
            hours: Number of hours of history to retrieve
            
        Returns:
            List of metric dictionaries
        """
        if not self.redis_client:
            return []
        
        try:
            base_key = f"{self.metrics_prefix}{metric_type}:history"
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(hours=hours)
            
            # Get all keys in the time range
            pattern = f"{base_key}:*"
            keys = self.redis_client.keys(pattern)
            
            metrics = []
            for key in keys:
                try:
                    # Extract timestamp from key
                    timestamp_str = key.split(':')[-1]
                    timestamp = datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc)
                    
                    if timestamp >= start_time:
                        data = self.redis_client.get(key)
                        if data:
                            metrics.append(json.loads(data))
                except (ValueError, json.JSONDecodeError):
                    continue
            
            # Sort by timestamp
            metrics.sort(key=lambda x: x.get('timestamp', ''))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting historical metrics: {sanitize_for_log(str(e))}")
            return []
    
    def cleanup_old_metrics(self):
        """Clean up old metrics from Redis"""
        if not self.redis_client:
            return
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.metrics_retention_hours)
            cutoff_timestamp = int(cutoff_time.timestamp())
            
            # Clean up each metric type
            for metric_type in ['health', 'performance', 'errors', 'resources']:
                pattern = f"{self.metrics_prefix}{metric_type}:history:*"
                keys = self.redis_client.keys(pattern)
                
                deleted_count = 0
                for key in keys:
                    try:
                        timestamp_str = key.split(':')[-1]
                        timestamp = int(timestamp_str)
                        
                        if timestamp < cutoff_timestamp:
                            self.redis_client.delete(key)
                            deleted_count += 1
                    except ValueError:
                        continue
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old {metric_type} metrics")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {sanitize_for_log(str(e))}")
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Data Retention Manager

Manages data retention policies, automatic cleanup, and Redis memory monitoring
for RQ task data with configurable TTL management and referential integrity.
"""

import logging
import json
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import redis
from rq import Queue
from rq.registry import FinishedJobRegistry, FailedJobRegistry, StartedJobRegistry

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus
from .rq_config import RQConfig
from .rq_retention_config import get_retention_config_manager, RQRetentionConfig

logger = logging.getLogger(__name__)


from .retention_policy import RetentionPolicy


class RQDataRetentionManager:
    """Manages data retention and cleanup for RQ system"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection: redis.Redis, 
                 config: RQConfig, queues: Dict[str, Queue]):
        """
        Initialize RQ Data Retention Manager
        
        Args:
            db_manager: Database manager instance
            redis_connection: Redis connection
            config: RQ configuration
            queues: Dictionary of RQ queues
        """
        self.db_manager = db_manager
        self.redis_connection = redis_connection
        self.config = config
        self.queues = queues
        
        # Load retention configuration
        self.retention_config_manager = get_retention_config_manager()
        self.retention_config = self.retention_config_manager.get_config()
        
        # Retention policies
        self.retention_policies = self._initialize_retention_policies()
        self.active_policy = self.retention_config_manager.create_retention_policy(
            self.retention_config.active_policy_name
        )
        
        # Monitoring
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        
        # Redis key patterns
        self.task_data_pattern = "rq:task:*"
        self.progress_data_pattern = "rq:progress:*"
        self.security_logs_pattern = "rq:security:events:*"
        self.worker_auth_pattern = "rq:security:worker_auth:*"
        self.task_auth_pattern = "rq:security:task_auth:*"
        
        # Cleanup statistics
        self.cleanup_stats = {
            'last_cleanup': None,
            'total_cleanups': 0,
            'items_cleaned': 0,
            'memory_freed_mb': 0,
            'errors': 0
        }
        
        logger.info("RQ Data Retention Manager initialized")
    
    def _initialize_retention_policies(self) -> Dict[str, RetentionPolicy]:
        """Initialize predefined retention policies"""
        policies = {
            'default': RetentionPolicy(
                name='default',
                description='Default retention policy for production use',
                completed_tasks_ttl=86400,      # 24 hours
                failed_tasks_ttl=259200,        # 72 hours
                cancelled_tasks_ttl=43200,      # 12 hours
                progress_data_ttl=3600,         # 1 hour
                security_logs_ttl=604800,       # 7 days
                max_memory_usage_mb=512,        # 512 MB
                cleanup_threshold_mb=400,       # 400 MB
                cleanup_batch_size=100
            ),
            'development': RetentionPolicy(
                name='development',
                description='Development retention policy with shorter TTLs',
                completed_tasks_ttl=3600,       # 1 hour
                failed_tasks_ttl=7200,          # 2 hours
                cancelled_tasks_ttl=1800,       # 30 minutes
                progress_data_ttl=900,          # 15 minutes
                security_logs_ttl=86400,        # 1 day
                max_memory_usage_mb=128,        # 128 MB
                cleanup_threshold_mb=100,       # 100 MB
                cleanup_batch_size=50
            ),
            'high_volume': RetentionPolicy(
                name='high_volume',
                description='High volume retention policy with aggressive cleanup',
                completed_tasks_ttl=43200,      # 12 hours
                failed_tasks_ttl=86400,         # 24 hours
                cancelled_tasks_ttl=3600,       # 1 hour
                progress_data_ttl=1800,         # 30 minutes
                security_logs_ttl=259200,       # 3 days
                max_memory_usage_mb=1024,       # 1 GB
                cleanup_threshold_mb=800,       # 800 MB
                cleanup_batch_size=200
            ),
            'conservative': RetentionPolicy(
                name='conservative',
                description='Conservative retention policy with longer TTLs',
                completed_tasks_ttl=604800,     # 7 days
                failed_tasks_ttl=1209600,       # 14 days
                cancelled_tasks_ttl=259200,     # 3 days
                progress_data_ttl=86400,        # 1 day
                security_logs_ttl=2592000,      # 30 days
                max_memory_usage_mb=2048,       # 2 GB
                cleanup_threshold_mb=1600,      # 1.6 GB
                cleanup_batch_size=50
            )
        }
        
        return policies
    
    def set_retention_policy(self, policy_name: str) -> bool:
        """
        Set active retention policy
        
        Args:
            policy_name: Name of the retention policy to activate
            
        Returns:
            True if policy was set successfully
        """
        try:
            # Check if policy exists (predefined or custom)
            available_policies = self.retention_config_manager.get_available_policies()
            if policy_name not in available_policies:
                logger.error(f"Unknown retention policy: {sanitize_for_log(policy_name)}")
                return False
            
            old_policy = self.active_policy.name
            
            # Create new policy using configuration manager
            self.active_policy = self.retention_config_manager.create_retention_policy(policy_name)
            
            # Update configuration
            self.retention_config.active_policy_name = policy_name
            
            logger.info(f"Changed retention policy from {old_policy} to {policy_name}")
            
            # Apply new TTLs to existing data
            self._apply_policy_to_existing_data()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set retention policy: {sanitize_for_log(str(e))}")
            return False
    
    def _apply_policy_to_existing_data(self) -> None:
        """Apply current retention policy TTLs to existing Redis data"""
        try:
            policy = self.active_policy
            
            # Update task data TTLs
            for key in self.redis_connection.scan_iter(match=self.task_data_pattern):
                self.redis_connection.expire(key, policy.completed_tasks_ttl)
            
            # Update progress data TTLs
            for key in self.redis_connection.scan_iter(match=self.progress_data_pattern):
                self.redis_connection.expire(key, policy.progress_data_ttl)
            
            # Update security logs TTLs
            for key in self.redis_connection.scan_iter(match=self.security_logs_pattern):
                self.redis_connection.expire(key, policy.security_logs_ttl)
            
            logger.info("Applied retention policy TTLs to existing data")
            
        except Exception as e:
            logger.error(f"Failed to apply policy to existing data: {sanitize_for_log(str(e))}")
    
    def set_task_ttl(self, task_id: str, status: TaskStatus) -> None:
        """
        Set TTL for task data based on status and retention policy
        
        Args:
            task_id: Task identifier
            status: Task status to determine appropriate TTL
        """
        try:
            policy = self.active_policy
            
            # Determine TTL based on status
            ttl_map = {
                TaskStatus.COMPLETED: policy.completed_tasks_ttl,
                TaskStatus.FAILED: policy.failed_tasks_ttl,
                TaskStatus.CANCELLED: policy.cancelled_tasks_ttl
            }
            
            ttl = ttl_map.get(status)
            if ttl is None:
                # For running/queued tasks, don't set TTL
                return
            
            # Set TTL for task-related keys
            task_patterns = [
                f"rq:task:{task_id}",
                f"rq:progress:{task_id}",
                f"rq:security:task_auth:{task_id}"
            ]
            
            for pattern in task_patterns:
                for key in self.redis_connection.scan_iter(match=pattern):
                    self.redis_connection.expire(key, ttl)
            
            logger.debug(f"Set TTL {ttl}s for task {sanitize_for_log(task_id)} with status {status.value}")
            
        except Exception as e:
            logger.error(f"Failed to set task TTL: {sanitize_for_log(str(e))}")
    
    def cleanup_expired_data(self) -> Dict[str, Any]:
        """
        Clean up expired data and enforce retention policies
        
        Returns:
            Dictionary containing cleanup results
        """
        try:
            cleanup_start = datetime.now(timezone.utc)
            results = {
                'started_at': cleanup_start.isoformat(),
                'policy': self.active_policy.name,
                'items_cleaned': 0,
                'memory_freed_mb': 0,
                'categories': {},
                'errors': []
            }
            
            # Get memory usage before cleanup
            memory_before = self._get_redis_memory_usage()
            
            # Clean up different data categories
            categories = [
                ('completed_tasks', self.task_data_pattern, self.active_policy.completed_tasks_ttl),
                ('progress_data', self.progress_data_pattern, self.active_policy.progress_data_ttl),
                ('security_logs', self.security_logs_pattern, self.active_policy.security_logs_ttl),
                ('worker_auth', self.worker_auth_pattern, 3600),  # 1 hour for auth data
                ('task_auth', self.task_auth_pattern, 7200)       # 2 hours for task auth
            ]
            
            for category, pattern, max_age in categories:
                try:
                    cleaned = self._cleanup_category(pattern, max_age)
                    results['categories'][category] = cleaned
                    results['items_cleaned'] += cleaned
                except Exception as e:
                    error_msg = f"Failed to cleanup {category}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(sanitize_for_log(error_msg))
            
            # Clean up RQ job registries
            registry_cleaned = self._cleanup_job_registries()
            results['categories']['job_registries'] = registry_cleaned
            results['items_cleaned'] += registry_cleaned
            
            # Calculate memory freed
            memory_after = self._get_redis_memory_usage()
            results['memory_freed_mb'] = max(0, memory_before - memory_after)
            
            # Update statistics
            self.cleanup_stats['last_cleanup'] = cleanup_start.isoformat()
            self.cleanup_stats['total_cleanups'] += 1
            self.cleanup_stats['items_cleaned'] += results['items_cleaned']
            self.cleanup_stats['memory_freed_mb'] += results['memory_freed_mb']
            self.cleanup_stats['errors'] += len(results['errors'])
            
            results['completed_at'] = datetime.now(timezone.utc).isoformat()
            results['duration_seconds'] = (datetime.now(timezone.utc) - cleanup_start).total_seconds()
            
            logger.info(f"Cleanup completed: {results['items_cleaned']} items, {results['memory_freed_mb']:.2f}MB freed")
            
            return results
            
        except Exception as e:
            logger.error(f"Cleanup failed: {sanitize_for_log(str(e))}")
            return {'error': str(e), 'items_cleaned': 0}
    
    def _cleanup_category(self, pattern: str, max_age_seconds: int) -> int:
        """Clean up a specific category of Redis keys"""
        try:
            cleaned_count = 0
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
            
            for key in self.redis_connection.scan_iter(match=pattern):
                try:
                    # Check if key has expired or should be cleaned
                    ttl = self.redis_connection.ttl(key)
                    
                    if ttl == -2:  # Key doesn't exist
                        continue
                    elif ttl == -1:  # Key exists but has no TTL
                        # Check if key is old enough to be cleaned
                        if self._is_key_expired(key, cutoff_time):
                            self.redis_connection.delete(key)
                            cleaned_count += 1
                    elif ttl == 0:  # Key has expired
                        self.redis_connection.delete(key)
                        cleaned_count += 1
                    
                    # Batch processing to avoid blocking Redis
                    if cleaned_count % self.active_policy.cleanup_batch_size == 0:
                        time.sleep(0.001)  # Small delay to prevent Redis blocking
                        
                except Exception as key_error:
                    logger.warning(f"Error cleaning key {sanitize_for_log(key.decode())}: {sanitize_for_log(str(key_error))}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Category cleanup failed for pattern {pattern}: {sanitize_for_log(str(e))}")
            return 0
    
    def _is_key_expired(self, key: bytes, cutoff_time: datetime) -> bool:
        """Check if a key should be considered expired based on its data"""
        try:
            # Try to get timestamp from key data
            key_str = key.decode()
            
            # Check if key contains timestamp information
            if 'events:' in key_str:
                # Security events keys contain date in format YYYYMMDD
                date_match = key_str.split('events:')[-1][:8]
                try:
                    key_date = datetime.strptime(date_match, '%Y%m%d').replace(tzinfo=timezone.utc)
                    return key_date < cutoff_time
                except ValueError:
                    pass
            
            # For other keys, check if they have associated metadata
            try:
                data = self.redis_connection.get(key)
                if data:
                    # Try to parse as JSON and look for timestamp
                    try:
                        json_data = json.loads(data.decode())
                        if isinstance(json_data, dict):
                            timestamp_fields = ['created_at', 'timestamp', 'registered_at']
                            for field in timestamp_fields:
                                if field in json_data:
                                    key_time = datetime.fromisoformat(json_data[field].replace('Z', '+00:00'))
                                    return key_time < cutoff_time
                    except (json.JSONDecodeError, ValueError):
                        pass
            except Exception:
                pass
            
            # If no timestamp found, consider it expired if it's old enough
            return False
            
        except Exception as e:
            logger.debug(f"Error checking key expiration: {sanitize_for_log(str(e))}")
            return False
    
    def _cleanup_job_registries(self) -> int:
        """Clean up RQ job registries"""
        try:
            cleaned_count = 0
            
            for queue_name, queue in self.queues.items():
                try:
                    # Clean finished jobs
                    finished_registry = FinishedJobRegistry(queue=queue)
                    finished_cleaned = finished_registry.cleanup()
                    cleaned_count += finished_cleaned
                    
                    # Clean failed jobs older than policy
                    failed_registry = FailedJobRegistry(queue=queue)
                    failed_cleaned = failed_registry.cleanup()
                    cleaned_count += failed_cleaned
                    
                    # Clean started jobs that are stuck
                    started_registry = StartedJobRegistry(queue=queue)
                    # Note: StartedJobRegistry cleanup is more complex and should be done carefully
                    # We'll implement this in a future enhancement
                    
                    if finished_cleaned > 0 or failed_cleaned > 0:
                        logger.debug(f"Cleaned {finished_cleaned} finished and {failed_cleaned} failed jobs from {queue_name}")
                        
                except Exception as queue_error:
                    logger.warning(f"Error cleaning registry for queue {queue_name}: {sanitize_for_log(str(queue_error))}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Job registry cleanup failed: {sanitize_for_log(str(e))}")
            return 0
    
    def _get_redis_memory_usage(self) -> float:
        """Get current Redis memory usage in MB"""
        try:
            info = self.redis_connection.info('memory')
            used_memory = info.get('used_memory', 0)
            return used_memory / (1024 * 1024)  # Convert to MB
        except Exception as e:
            logger.warning(f"Failed to get Redis memory usage: {sanitize_for_log(str(e))}")
            return 0.0
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """
        Check Redis memory usage and trigger cleanup if needed
        
        Returns:
            Dictionary containing memory status and actions taken
        """
        try:
            current_usage_mb = self._get_redis_memory_usage()
            policy = self.active_policy
            
            status = {
                'current_usage_mb': current_usage_mb,
                'max_usage_mb': policy.max_memory_usage_mb,
                'cleanup_threshold_mb': policy.cleanup_threshold_mb,
                'usage_percentage': (current_usage_mb / policy.max_memory_usage_mb) * 100,
                'action_taken': None,
                'cleanup_triggered': False
            }
            
            # Check if cleanup is needed
            if current_usage_mb > policy.cleanup_threshold_mb:
                logger.warning(f"Redis memory usage ({current_usage_mb:.2f}MB) exceeds cleanup threshold ({policy.cleanup_threshold_mb}MB)")
                
                # Trigger cleanup
                cleanup_results = self.cleanup_expired_data()
                status['action_taken'] = 'automatic_cleanup'
                status['cleanup_triggered'] = True
                status['cleanup_results'] = cleanup_results
                
                # Check if emergency cleanup is needed
                new_usage_mb = self._get_redis_memory_usage()
                if new_usage_mb > policy.max_memory_usage_mb:
                    logger.critical(f"Redis memory usage ({new_usage_mb:.2f}MB) still exceeds maximum ({policy.max_memory_usage_mb}MB) after cleanup")
                    
                    # Trigger emergency cleanup
                    emergency_results = self._emergency_cleanup()
                    status['action_taken'] = 'emergency_cleanup'
                    status['emergency_results'] = emergency_results
            
            elif current_usage_mb > policy.max_memory_usage_mb * 0.8:  # 80% threshold
                logger.info(f"Redis memory usage ({current_usage_mb:.2f}MB) approaching limit ({policy.max_memory_usage_mb}MB)")
                status['action_taken'] = 'warning_logged'
            
            return status
            
        except Exception as e:
            logger.error(f"Memory usage check failed: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
    
    def _emergency_cleanup(self) -> Dict[str, Any]:
        """Perform emergency cleanup when memory usage is critical"""
        try:
            logger.warning("Performing emergency Redis cleanup")
            
            results = {
                'emergency_cleanup': True,
                'items_cleaned': 0,
                'actions': []
            }
            
            # More aggressive cleanup with shorter TTLs
            emergency_patterns = [
                (self.progress_data_pattern, 300),    # 5 minutes for progress data
                (self.task_data_pattern, 1800),       # 30 minutes for task data
                (self.worker_auth_pattern, 600),      # 10 minutes for worker auth
                (self.task_auth_pattern, 900)         # 15 minutes for task auth
            ]
            
            for pattern, emergency_ttl in emergency_patterns:
                cleaned = self._cleanup_category(pattern, emergency_ttl)
                results['items_cleaned'] += cleaned
                results['actions'].append(f"Cleaned {cleaned} items from {pattern}")
            
            # Force cleanup of all job registries
            for queue_name, queue in self.queues.items():
                try:
                    finished_registry = FinishedJobRegistry(queue=queue)
                    failed_registry = FailedJobRegistry(queue=queue)
                    
                    # Clear all finished and failed jobs
                    finished_jobs = finished_registry.get_job_ids()
                    failed_jobs = failed_registry.get_job_ids()
                    
                    for job_id in finished_jobs:
                        finished_registry.remove(job_id)
                    
                    for job_id in failed_jobs:
                        failed_registry.remove(job_id)
                    
                    cleaned_jobs = len(finished_jobs) + len(failed_jobs)
                    results['items_cleaned'] += cleaned_jobs
                    results['actions'].append(f"Force cleaned {cleaned_jobs} jobs from {queue_name}")
                    
                except Exception as queue_error:
                    logger.error(f"Emergency cleanup failed for queue {queue_name}: {sanitize_for_log(str(queue_error))}")
            
            logger.warning(f"Emergency cleanup completed: {results['items_cleaned']} items cleaned")
            return results
            
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {sanitize_for_log(str(e))}")
            return {'error': str(e), 'items_cleaned': 0}
    
    def start_monitoring(self, check_interval: int = None) -> None:
        """
        Start automatic memory monitoring and cleanup
        
        Args:
            check_interval: Interval between checks in seconds (uses config default if None)
        """
        if self._monitoring_active:
            logger.warning("Memory monitoring is already active")
            return
        
        # Use configuration if monitoring is enabled
        if not self.retention_config.monitoring_enabled:
            logger.info("Memory monitoring disabled by configuration")
            return
        
        if check_interval is None:
            check_interval = self.retention_config.monitoring_interval
        
        try:
            self._stop_monitoring.clear()
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                args=(check_interval,),
                daemon=True,
                name="RQDataRetentionMonitor"
            )
            self._monitoring_thread.start()
            self._monitoring_active = True
            
            logger.info(f"Started RQ data retention monitoring with {check_interval}s interval")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {sanitize_for_log(str(e))}")
    
    def stop_monitoring(self) -> None:
        """Stop automatic memory monitoring"""
        if not self._monitoring_active:
            return
        
        try:
            self._stop_monitoring.set()
            
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=10)
            
            self._monitoring_active = False
            logger.info("Stopped RQ data retention monitoring")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {sanitize_for_log(str(e))}")
    
    def _monitoring_loop(self, check_interval: int) -> None:
        """Main monitoring loop"""
        logger.info("RQ data retention monitoring loop started")
        
        while not self._stop_monitoring.wait(check_interval):
            try:
                # Check memory usage and trigger cleanup if needed
                memory_status = self.check_memory_usage()
                
                # Log status periodically
                if memory_status.get('usage_percentage', 0) > 50:
                    logger.info(f"Redis memory usage: {memory_status.get('current_usage_mb', 0):.2f}MB "
                              f"({memory_status.get('usage_percentage', 0):.1f}%)")
                
                # Perform regular cleanup even if not at threshold
                if self.cleanup_stats['total_cleanups'] == 0 or \
                   (datetime.now(timezone.utc) - datetime.fromisoformat(self.cleanup_stats['last_cleanup'])).total_seconds() > 3600:
                    self.cleanup_expired_data()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {sanitize_for_log(str(e))}")
                time.sleep(60)  # Wait before retrying
        
        logger.info("RQ data retention monitoring loop stopped")
    
    def get_retention_status(self) -> Dict[str, Any]:
        """
        Get comprehensive retention status and statistics
        
        Returns:
            Dictionary containing retention status information
        """
        try:
            current_usage_mb = self._get_redis_memory_usage()
            
            status = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'active_policy': {
                    'name': self.active_policy.name,
                    'description': self.active_policy.description,
                    'ttls': {
                        'completed_tasks': self.active_policy.completed_tasks_ttl,
                        'failed_tasks': self.active_policy.failed_tasks_ttl,
                        'cancelled_tasks': self.active_policy.cancelled_tasks_ttl,
                        'progress_data': self.active_policy.progress_data_ttl,
                        'security_logs': self.active_policy.security_logs_ttl
                    },
                    'memory_limits': {
                        'max_usage_mb': self.active_policy.max_memory_usage_mb,
                        'cleanup_threshold_mb': self.active_policy.cleanup_threshold_mb
                    }
                },
                'memory_usage': {
                    'current_mb': current_usage_mb,
                    'max_mb': self.active_policy.max_memory_usage_mb,
                    'usage_percentage': (current_usage_mb / self.active_policy.max_memory_usage_mb) * 100,
                    'threshold_mb': self.active_policy.cleanup_threshold_mb
                },
                'monitoring': {
                    'active': self._monitoring_active,
                    'thread_alive': self._monitoring_thread.is_alive() if self._monitoring_thread else False
                },
                'cleanup_statistics': self.cleanup_stats.copy(),
                'available_policies': list(self.retention_policies.keys())
            }
            
            # Add data counts
            status['data_counts'] = self._get_data_counts()
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get retention status: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
    
    def _get_data_counts(self) -> Dict[str, int]:
        """Get counts of different types of data in Redis"""
        try:
            counts = {}
            
            patterns = {
                'task_data': self.task_data_pattern,
                'progress_data': self.progress_data_pattern,
                'security_logs': self.security_logs_pattern,
                'worker_auth': self.worker_auth_pattern,
                'task_auth': self.task_auth_pattern
            }
            
            for name, pattern in patterns.items():
                try:
                    count = len(list(self.redis_connection.scan_iter(match=pattern)))
                    counts[name] = count
                except Exception as e:
                    logger.warning(f"Failed to count {name}: {sanitize_for_log(str(e))}")
                    counts[name] = -1
            
            return counts
            
        except Exception as e:
            logger.error(f"Failed to get data counts: {sanitize_for_log(str(e))}")
            return {}
    
    def force_cleanup(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Force immediate cleanup of specified category or all data
        
        Args:
            category: Optional category to clean ('task_data', 'progress_data', etc.)
                     If None, cleans all categories
            
        Returns:
            Dictionary containing cleanup results
        """
        try:
            if category:
                # Clean specific category
                pattern_map = {
                    'task_data': self.task_data_pattern,
                    'progress_data': self.progress_data_pattern,
                    'security_logs': self.security_logs_pattern,
                    'worker_auth': self.worker_auth_pattern,
                    'task_auth': self.task_auth_pattern
                }
                
                if category not in pattern_map:
                    return {'error': f'Unknown category: {category}'}
                
                pattern = pattern_map[category]
                cleaned = self._cleanup_category(pattern, 0)  # Clean all items
                
                return {
                    'category': category,
                    'items_cleaned': cleaned,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                # Clean all categories
                return self.cleanup_expired_data()
                
        except Exception as e:
            logger.error(f"Force cleanup failed: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
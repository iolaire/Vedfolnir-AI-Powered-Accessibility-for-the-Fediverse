# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Priority Queue Handler for Task Distribution

Manages priority-based task distribution and processing order with round-robin
processing within same priority level and retry logic with exponential backoff.
"""

import logging
import time
import random
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import redis
from rq import Queue, Job
from rq.exceptions import NoSuchJobError

from app.core.security.core.security_utils import sanitize_for_log
from .rq_config import TaskPriority, RetryPolicy
from .task_serializer import RQTaskData

logger = logging.getLogger(__name__)


class PriorityQueueHandler:
    """Manages priority-based task distribution and processing order"""
    
    def __init__(self, redis_connection: redis.Redis, queues: Dict[str, Queue]):
        """
        Initialize Priority Queue Handler
        
        Args:
            redis_connection: Redis connection instance
            queues: Dictionary of priority -> Queue mappings
        """
        self.redis = redis_connection
        self.queues = queues
        self.priority_order = [
            TaskPriority.URGENT.value,
            TaskPriority.HIGH.value,
            TaskPriority.NORMAL.value,
            TaskPriority.LOW.value
        ]
        
        # Round-robin tracking for same priority level
        self._round_robin_state = {}
        for priority in self.priority_order:
            self._round_robin_state[priority] = 0
        
        # Retry tracking
        self._retry_prefix = "vedfolnir:rq:retry:"
        self._failed_job_prefix = "vedfolnir:rq:failed:"
    
    def get_next_task(self, worker_queues: List[str]) -> Optional[Job]:
        """
        Get next task to execute, considering priority and round-robin within same priority
        
        Args:
            worker_queues: List of queue names this worker can process
            
        Returns:
            Job: Next job to process or None if no jobs available
        """
        try:
            # Process queues in strict priority order
            for priority in self.priority_order:
                if priority not in worker_queues:
                    continue
                
                queue = self.queues.get(priority)
                if not queue:
                    continue
                
                # Get job from this priority queue
                job = self._get_job_from_queue(queue, priority)
                if job:
                    logger.info(f"Retrieved job {sanitize_for_log(job.id)} from {priority} queue")
                    return job
            
            # No jobs available in any queue
            return None
            
        except Exception as e:
            logger.error(f"Error getting next task: {sanitize_for_log(str(e))}")
            return None
    
    def _get_job_from_queue(self, queue: Queue, priority: str) -> Optional[Job]:
        """Get job from specific queue with round-robin logic"""
        try:
            # For now, RQ handles job ordering within queues (FIFO)
            # Round-robin can be implemented here if multiple jobs are available
            job = queue.dequeue()
            
            if job:
                # Update round-robin state
                self._round_robin_state[priority] = (self._round_robin_state[priority] + 1) % 1000
                
                # Check if job needs retry handling
                if self._is_retry_job(job):
                    retry_info = self._get_retry_info(job.id)
                    if retry_info and not self._should_retry_now(retry_info):
                        # Job not ready for retry yet, requeue it
                        self._requeue_for_later_retry(job, retry_info)
                        return None
            
            return job
            
        except Exception as e:
            logger.error(f"Error getting job from {priority} queue: {sanitize_for_log(str(e))}")
            return None
    
    def enqueue_by_priority(self, queue: Queue, job_func: str, task_data: RQTaskData, 
                           priority: TaskPriority, timeout: int = None) -> Optional[Job]:
        """
        Enqueue task to appropriate priority queue
        
        Args:
            queue: Queue to enqueue to
            job_func: Job function to execute
            task_data: Task data to process
            priority: Task priority
            timeout: Job timeout in seconds
            
        Returns:
            Job: Enqueued job or None if failed
        """
        try:
            # Enqueue job with task data
            job = queue.enqueue(
                job_func,
                task_data.task_id,
                job_id=task_data.task_id,
                job_timeout=timeout,
                meta={'priority': priority.value, 'retry_count': task_data.retry_count}
            )
            
            logger.info(f"Enqueued job {sanitize_for_log(job.id)} to {priority.value} queue")
            return job
            
        except Exception as e:
            logger.error(f"Failed to enqueue job to {priority.value} queue: {sanitize_for_log(str(e))}")
            return None
    
    def requeue_failed_task(self, job: Job, retry_policy: RetryPolicy) -> bool:
        """
        Requeue failed task with exponential backoff
        
        Args:
            job: Failed job to requeue
            retry_policy: Retry policy configuration
            
        Returns:
            bool: True if requeued, False if max retries exceeded
        """
        try:
            # Get current retry count
            retry_count = job.meta.get('retry_count', 0)
            
            if retry_count >= retry_policy.max_retries:
                logger.warning(f"Job {sanitize_for_log(job.id)} exceeded max retries ({retry_policy.max_retries})")
                self._move_to_dead_letter_queue(job)
                return False
            
            # Calculate retry delay
            delay = self._calculate_retry_delay(retry_count, retry_policy)
            
            # Store retry information
            retry_info = {
                'job_id': job.id,
                'retry_count': retry_count + 1,
                'next_retry_time': (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat(),
                'original_queue': job.meta.get('priority', TaskPriority.NORMAL.value),
                'failure_reason': str(job.exc_info) if job.exc_info else 'Unknown error',
                'retry_policy': {
                    'max_retries': retry_policy.max_retries,
                    'backoff_strategy': retry_policy.backoff_strategy,
                    'base_delay': retry_policy.base_delay,
                    'max_delay': retry_policy.max_delay
                }
            }
            
            self._store_retry_info(job.id, retry_info)
            
            # Requeue job with updated retry count
            original_queue_name = job.meta.get('priority', TaskPriority.NORMAL.value)
            queue = self.queues.get(original_queue_name)
            
            if queue:
                # Update job metadata
                job.meta['retry_count'] = retry_count + 1
                job.save_meta()
                
                # Enqueue for retry after delay
                retry_job = queue.enqueue_in(
                    delay,
                    job.func_name,
                    *job.args,
                    **job.kwargs,
                    job_id=f"{job.id}_retry_{retry_count + 1}",
                    meta=job.meta
                )
                
                logger.info(f"Requeued job {sanitize_for_log(job.id)} for retry {retry_count + 1} after {delay}s delay")
                return True
            else:
                logger.error(f"Original queue {original_queue_name} not found for retry")
                return False
                
        except Exception as e:
            logger.error(f"Failed to requeue job {sanitize_for_log(job.id)}: {sanitize_for_log(str(e))}")
            return False
    
    def _calculate_retry_delay(self, retry_count: int, retry_policy: RetryPolicy) -> int:
        """Calculate retry delay based on backoff strategy"""
        try:
            if retry_policy.backoff_strategy == 'exponential':
                # Exponential backoff: base_delay * (2 ^ retry_count)
                delay = retry_policy.base_delay * (2 ** retry_count)
            elif retry_policy.backoff_strategy == 'linear':
                # Linear backoff: base_delay * retry_count
                delay = retry_policy.base_delay * (retry_count + 1)
            elif retry_policy.backoff_strategy == 'fixed':
                # Fixed delay
                delay = retry_policy.base_delay
            else:
                # Default to exponential
                delay = retry_policy.base_delay * (2 ** retry_count)
            
            # Apply jitter to prevent thundering herd
            jitter = random.uniform(0.8, 1.2)
            delay = int(delay * jitter)
            
            # Ensure delay doesn't exceed max_delay
            delay = min(delay, retry_policy.max_delay)
            
            # Ensure minimum delay of 1 second
            delay = max(delay, 1)
            
            return delay
            
        except Exception as e:
            logger.error(f"Error calculating retry delay: {sanitize_for_log(str(e))}")
            return retry_policy.base_delay
    
    def _store_retry_info(self, job_id: str, retry_info: Dict[str, Any]) -> None:
        """Store retry information in Redis"""
        try:
            key = f"{self._retry_prefix}{job_id}"
            self.redis.setex(key, 86400, str(retry_info))  # 24 hour TTL
        except Exception as e:
            logger.error(f"Failed to store retry info for job {sanitize_for_log(job_id)}: {sanitize_for_log(str(e))}")
    
    def _get_retry_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get retry information from Redis"""
        try:
            key = f"{self._retry_prefix}{job_id}"
            retry_data = self.redis.get(key)
            if retry_data:
                import ast
                return ast.literal_eval(retry_data.decode('utf-8'))
            return None
        except Exception as e:
            logger.error(f"Failed to get retry info for job {sanitize_for_log(job_id)}: {sanitize_for_log(str(e))}")
            return None
    
    def _is_retry_job(self, job: Job) -> bool:
        """Check if job is a retry job"""
        return job.meta.get('retry_count', 0) > 0
    
    def _should_retry_now(self, retry_info: Dict[str, Any]) -> bool:
        """Check if job should be retried now based on retry time"""
        try:
            next_retry_time_str = retry_info.get('next_retry_time')
            if not next_retry_time_str:
                return True
            
            next_retry_time = datetime.fromisoformat(next_retry_time_str.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) >= next_retry_time
            
        except Exception as e:
            logger.error(f"Error checking retry time: {sanitize_for_log(str(e))}")
            return True  # Default to allowing retry
    
    def _requeue_for_later_retry(self, job: Job, retry_info: Dict[str, Any]) -> None:
        """Requeue job for later retry"""
        try:
            # Calculate remaining delay
            next_retry_time_str = retry_info.get('next_retry_time')
            next_retry_time = datetime.fromisoformat(next_retry_time_str.replace('Z', '+00:00'))
            delay = max(1, int((next_retry_time - datetime.now(timezone.utc)).total_seconds()))
            
            # Get original queue
            original_queue_name = retry_info.get('original_queue', TaskPriority.NORMAL.value)
            queue = self.queues.get(original_queue_name)
            
            if queue:
                queue.enqueue_in(
                    delay,
                    job.func_name,
                    *job.args,
                    **job.kwargs,
                    job_id=job.id,
                    meta=job.meta
                )
                logger.debug(f"Requeued job {sanitize_for_log(job.id)} for retry in {delay}s")
            
        except Exception as e:
            logger.error(f"Failed to requeue job for later retry: {sanitize_for_log(str(e))}")
    
    def _move_to_dead_letter_queue(self, job: Job) -> None:
        """Move job to dead letter queue after max retries exceeded"""
        try:
            # Store in failed jobs registry
            failed_key = f"{self._failed_job_prefix}{job.id}"
            failed_info = {
                'job_id': job.id,
                'original_queue': job.meta.get('priority', TaskPriority.NORMAL.value),
                'retry_count': job.meta.get('retry_count', 0),
                'failed_at': datetime.now(timezone.utc).isoformat(),
                'failure_reason': str(job.exc_info) if job.exc_info else 'Max retries exceeded',
                'job_args': job.args,
                'job_kwargs': job.kwargs
            }
            
            # Store with 7 day TTL
            self.redis.setex(failed_key, 604800, str(failed_info))
            
            logger.warning(f"Moved job {sanitize_for_log(job.id)} to dead letter queue after max retries")
            
        except Exception as e:
            logger.error(f"Failed to move job to dead letter queue: {sanitize_for_log(str(e))}")
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get statistics for all priority queues"""
        stats = {
            'queues': {},
            'total_pending': 0,
            'total_failed': 0,
            'total_finished': 0,
            'round_robin_state': self._round_robin_state.copy()
        }
        
        try:
            for priority, queue in self.queues.items():
                queue_stats = {
                    'pending': len(queue),
                    'failed': queue.failed_job_registry.count,
                    'finished': queue.finished_job_registry.count,
                    'started': queue.started_job_registry.count,
                    'deferred': queue.deferred_job_registry.count if hasattr(queue, 'deferred_job_registry') else 0
                }
                
                stats['queues'][priority] = queue_stats
                stats['total_pending'] += queue_stats['pending']
                stats['total_failed'] += queue_stats['failed']
                stats['total_finished'] += queue_stats['finished']
            
        except Exception as e:
            logger.error(f"Error getting queue statistics: {sanitize_for_log(str(e))}")
            stats['error'] = str(e)
        
        return stats
    
    def get_failed_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of failed jobs from dead letter queue"""
        failed_jobs = []
        
        try:
            pattern = f"{self._failed_job_prefix}*"
            keys = self.redis.keys(pattern)
            
            for key in keys[:limit]:
                try:
                    failed_data = self.redis.get(key)
                    if failed_data:
                        import ast
                        failed_info = ast.literal_eval(failed_data.decode('utf-8'))
                        failed_jobs.append(failed_info)
                except Exception as e:
                    logger.error(f"Error parsing failed job data: {sanitize_for_log(str(e))}")
                    continue
            
        except Exception as e:
            logger.error(f"Error getting failed jobs: {sanitize_for_log(str(e))}")
        
        return failed_jobs
    
    def retry_failed_job(self, job_id: str) -> bool:
        """Manually retry a failed job from dead letter queue"""
        try:
            failed_key = f"{self._failed_job_prefix}{job_id}"
            failed_data = self.redis.get(failed_key)
            
            if not failed_data:
                logger.warning(f"Failed job {sanitize_for_log(job_id)} not found in dead letter queue")
                return False
            
            import ast
            failed_info = ast.literal_eval(failed_data.decode('utf-8'))
            
            # Get original queue
            original_queue_name = failed_info.get('original_queue', TaskPriority.NORMAL.value)
            queue = self.queues.get(original_queue_name)
            
            if not queue:
                logger.error(f"Original queue {original_queue_name} not found")
                return False
            
            # Requeue job with reset retry count
            retry_job = queue.enqueue(
                'app.services.task.rq.rq_job_processor.process_caption_task',
                *failed_info.get('job_args', []),
                **failed_info.get('job_kwargs', {}),
                job_id=f"{job_id}_manual_retry",
                meta={'retry_count': 0, 'priority': original_queue_name}
            )
            
            # Remove from dead letter queue
            self.redis.delete(failed_key)
            
            logger.info(f"Manually retried failed job {sanitize_for_log(job_id)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to manually retry job {sanitize_for_log(job_id)}: {sanitize_for_log(str(e))}")
            return False
    
    def cleanup_old_retry_info(self, older_than_hours: int = 24) -> int:
        """Clean up old retry information"""
        try:
            pattern = f"{self._retry_prefix}*"
            keys = self.redis.keys(pattern)
            
            cleaned_count = 0
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            
            for key in keys:
                try:
                    retry_data = self.redis.get(key)
                    if retry_data:
                        import ast
                        retry_info = ast.literal_eval(retry_data.decode('utf-8'))
                        next_retry_time_str = retry_info.get('next_retry_time')
                        
                        if next_retry_time_str:
                            next_retry_time = datetime.fromisoformat(next_retry_time_str.replace('Z', '+00:00'))
                            if next_retry_time < cutoff_time:
                                self.redis.delete(key)
                                cleaned_count += 1
                except Exception:
                    # If we can't parse the data, delete it
                    self.redis.delete(key)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old retry info entries")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up retry info: {sanitize_for_log(str(e))}")
            return 0
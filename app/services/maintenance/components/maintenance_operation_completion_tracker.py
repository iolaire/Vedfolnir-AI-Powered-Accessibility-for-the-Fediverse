# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Operation Completion Tracker

Tracks operation completion for jobs started before maintenance mode was enabled,
providing monitoring of active jobs during maintenance mode and completion notifications.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

from database import DatabaseManager
from models import CaptionGenerationTask, TaskStatus, User

logger = logging.getLogger(__name__)


@dataclass
class ActiveJobInfo:
    """Information about an active job during maintenance"""
    job_id: str
    user_id: int
    job_type: str
    started_at: datetime
    estimated_completion: Optional[datetime]
    status: str
    progress_percent: int
    current_step: Optional[str]
    platform_connection_id: Optional[int]


@dataclass
class CompletionNotification:
    """Notification about job completion"""
    job_id: str
    user_id: int
    job_type: str
    completion_status: str  # 'completed', 'failed', 'cancelled'
    completed_at: datetime
    duration_seconds: int
    error_message: Optional[str] = None


class MaintenanceOperationCompletionTracker:
    """
    Tracks operation completion during maintenance mode
    
    Features:
    - Monitors active jobs during maintenance mode
    - Tracks job completion and provides notifications
    - Updates active job count in maintenance status
    - Provides completion statistics and monitoring
    - Handles graceful job completion tracking
    """
    
    def __init__(self, db_manager: DatabaseManager, 
                 maintenance_service=None,
                 monitoring_interval: int = 30):
        """
        Initialize operation completion tracker
        
        Args:
            db_manager: Database manager instance
            maintenance_service: Enhanced maintenance mode service (optional)
            monitoring_interval: Interval in seconds for monitoring active jobs
        """
        self.db_manager = db_manager
        self.maintenance_service = maintenance_service
        self.monitoring_interval = monitoring_interval
        
        # Tracking state
        self._active_jobs: Dict[str, ActiveJobInfo] = {}
        self._completed_jobs: List[CompletionNotification] = []
        self._jobs_lock = threading.RLock()
        
        # Monitoring thread
        self._monitoring_thread: Optional[threading.Thread] = None
        self._monitoring_active = False
        self._shutdown_event = threading.Event()
        
        # Completion callbacks
        self._completion_callbacks: Dict[str, Callable] = {}
        self._callbacks_lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'jobs_tracked': 0,
            'jobs_completed': 0,
            'jobs_failed': 0,
            'jobs_cancelled': 0,
            'total_completion_time': 0,
            'average_completion_time': 0,
            'monitoring_cycles': 0,
            'last_monitoring_time': None
        }
        self._stats_lock = threading.RLock()
        
        logger.info("Maintenance operation completion tracker initialized")
    
    def start_monitoring(self) -> None:
        """Start monitoring active jobs during maintenance"""
        try:
            if self._monitoring_active:
                logger.warning("Job monitoring is already active")
                return
            
            self._monitoring_active = True
            self._shutdown_event.clear()
            
            # Start monitoring thread
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                name="MaintenanceJobMonitor",
                daemon=True
            )
            self._monitoring_thread.start()
            
            logger.info("Started maintenance job monitoring")
            
        except Exception as e:
            logger.error(f"Error starting job monitoring: {str(e)}")
            self._monitoring_active = False
            raise
    
    def stop_monitoring(self) -> None:
        """Stop monitoring active jobs"""
        try:
            if not self._monitoring_active:
                return
            
            logger.info("Stopping maintenance job monitoring")
            
            self._monitoring_active = False
            self._shutdown_event.set()
            
            # Wait for monitoring thread to finish
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=10)
                if self._monitoring_thread.is_alive():
                    logger.warning("Monitoring thread did not stop gracefully")
            
            logger.info("Maintenance job monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping job monitoring: {str(e)}")
    
    def get_active_jobs_count(self) -> int:
        """
        Get count of currently active jobs
        
        Returns:
            Number of active jobs being tracked
        """
        with self._jobs_lock:
            return len(self._active_jobs)
    
    def get_active_jobs(self) -> List[ActiveJobInfo]:
        """
        Get list of currently active jobs
        
        Returns:
            List of ActiveJobInfo objects
        """
        with self._jobs_lock:
            return list(self._active_jobs.values())
    
    def get_completed_jobs(self, limit: int = 50) -> List[CompletionNotification]:
        """
        Get list of recently completed jobs
        
        Args:
            limit: Maximum number of completed jobs to return
            
        Returns:
            List of CompletionNotification objects
        """
        with self._jobs_lock:
            # Return most recent completions first
            return self._completed_jobs[-limit:] if limit > 0 else self._completed_jobs[:]
    
    def get_completion_stats(self) -> Dict[str, Any]:
        """
        Get completion statistics
        
        Returns:
            Dictionary with completion statistics
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        with self._jobs_lock:
            stats.update({
                'current_active_jobs': len(self._active_jobs),
                'recent_completions': len(self._completed_jobs),
                'active_job_types': self._get_active_job_types(),
                'completion_rate': self._calculate_completion_rate()
            })
        
        return stats
    
    def subscribe_to_completions(self, callback: Callable[[CompletionNotification], None]) -> str:
        """
        Subscribe to job completion notifications
        
        Args:
            callback: Callback function to receive completion notifications
            
        Returns:
            Subscription ID
        """
        import uuid
        subscription_id = str(uuid.uuid4())
        
        with self._callbacks_lock:
            self._completion_callbacks[subscription_id] = callback
        
        logger.debug(f"Added completion subscription {subscription_id}")
        return subscription_id
    
    def unsubscribe_from_completions(self, subscription_id: str) -> bool:
        """
        Remove completion notification subscription
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed
        """
        with self._callbacks_lock:
            if subscription_id in self._completion_callbacks:
                del self._completion_callbacks[subscription_id]
                logger.debug(f"Removed completion subscription {subscription_id}")
                return True
        
        return False
    
    def force_refresh_active_jobs(self) -> int:
        """
        Force refresh of active jobs from database
        
        Returns:
            Number of active jobs found
        """
        try:
            active_jobs = self._query_active_jobs()
            
            with self._jobs_lock:
                # Clear current tracking
                self._active_jobs.clear()
                
                # Add all active jobs
                for job_info in active_jobs:
                    self._active_jobs[job_info.job_id] = job_info
            
            # Update maintenance service if available
            if self.maintenance_service:
                self.maintenance_service.update_active_jobs_count(len(active_jobs))
            
            logger.info(f"Force refreshed active jobs: {len(active_jobs)} jobs found")
            return len(active_jobs)
            
        except Exception as e:
            logger.error(f"Error force refreshing active jobs: {str(e)}")
            return 0
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs in background thread"""
        logger.info("Starting maintenance job monitoring loop")
        
        while self._monitoring_active and not self._shutdown_event.is_set():
            try:
                # Monitor active jobs
                self._monitor_active_jobs()
                
                # Update statistics
                with self._stats_lock:
                    self._stats['monitoring_cycles'] += 1
                    self._stats['last_monitoring_time'] = datetime.now(timezone.utc).isoformat()
                
                # Wait for next monitoring cycle
                if self._shutdown_event.wait(self.monitoring_interval):
                    break  # Shutdown requested
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                # Continue monitoring even if there's an error
                time.sleep(min(self.monitoring_interval, 60))  # Cap sleep time
        
        logger.info("Maintenance job monitoring loop stopped")
    
    def _monitor_active_jobs(self) -> None:
        """Monitor active jobs and detect completions"""
        try:
            # Query current active jobs from database
            current_active_jobs = self._query_active_jobs()
            current_job_ids = {job.job_id for job in current_active_jobs}
            
            with self._jobs_lock:
                # Find jobs that were active but are no longer active (completed)
                previously_active_ids = set(self._active_jobs.keys())
                completed_job_ids = previously_active_ids - current_job_ids
                
                # Process completed jobs
                for job_id in completed_job_ids:
                    if job_id in self._active_jobs:
                        self._handle_job_completion(job_id)
                
                # Update active jobs tracking
                self._active_jobs.clear()
                for job_info in current_active_jobs:
                    self._active_jobs[job_info.job_id] = job_info
            
            # Update maintenance service with current count
            if self.maintenance_service:
                self.maintenance_service.update_active_jobs_count(len(current_active_jobs))
            
            logger.debug(f"Monitored {len(current_active_jobs)} active jobs, {len(completed_job_ids)} completed")
            
        except Exception as e:
            logger.error(f"Error monitoring active jobs: {str(e)}")
    
    def _query_active_jobs(self) -> List[ActiveJobInfo]:
        """
        Query database for currently active jobs
        
        Returns:
            List of ActiveJobInfo objects for active jobs
        """
        try:
            with self.db_manager.get_session() as session:
                # Query active caption generation tasks
                active_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
                ).all()
                
                active_jobs = []
                for task in active_tasks:
                    # Estimate completion time based on progress and elapsed time
                    estimated_completion = None
                    if task.started_at and task.progress_percent > 0:
                        elapsed = datetime.now(timezone.utc) - task.started_at.replace(tzinfo=timezone.utc)
                        if task.progress_percent < 100:
                            total_estimated = elapsed * (100 / task.progress_percent)
                            remaining = total_estimated - elapsed
                            estimated_completion = datetime.now(timezone.utc) + remaining
                    
                    job_info = ActiveJobInfo(
                        job_id=task.id,
                        user_id=task.user_id,
                        job_type='caption_generation',
                        started_at=task.started_at or task.created_at,
                        estimated_completion=estimated_completion,
                        status=task.status.value,
                        progress_percent=task.progress_percent or 0,
                        current_step=task.current_step,
                        platform_connection_id=task.platform_connection_id
                    )
                    active_jobs.append(job_info)
                
                return active_jobs
                
        except Exception as e:
            logger.error(f"Error querying active jobs: {str(e)}")
            return []
    
    def _handle_job_completion(self, job_id: str) -> None:
        """
        Handle completion of a tracked job
        
        Args:
            job_id: ID of the completed job
        """
        try:
            # Get job info from tracking
            job_info = self._active_jobs.get(job_id)
            if not job_info:
                return
            
            # Query final job status from database
            completion_info = self._query_job_completion_info(job_id)
            if not completion_info:
                logger.warning(f"Could not get completion info for job {job_id}")
                return
            
            # Calculate duration
            duration_seconds = 0
            if job_info.started_at:
                duration = completion_info['completed_at'] - job_info.started_at.replace(tzinfo=timezone.utc)
                duration_seconds = int(duration.total_seconds())
            
            # Create completion notification
            notification = CompletionNotification(
                job_id=job_id,
                user_id=job_info.user_id,
                job_type=job_info.job_type,
                completion_status=completion_info['status'],
                completed_at=completion_info['completed_at'],
                duration_seconds=duration_seconds,
                error_message=completion_info.get('error_message')
            )
            
            # Add to completed jobs list
            with self._jobs_lock:
                self._completed_jobs.append(notification)
                # Keep only recent completions (last 100)
                if len(self._completed_jobs) > 100:
                    self._completed_jobs = self._completed_jobs[-100:]
            
            # Update statistics
            with self._stats_lock:
                self._stats['jobs_completed'] += 1
                if completion_info['status'] == 'completed':
                    self._stats['jobs_completed'] += 1
                elif completion_info['status'] == 'failed':
                    self._stats['jobs_failed'] += 1
                elif completion_info['status'] == 'cancelled':
                    self._stats['jobs_cancelled'] += 1
                
                self._stats['total_completion_time'] += duration_seconds
                if self._stats['jobs_completed'] > 0:
                    self._stats['average_completion_time'] = (
                        self._stats['total_completion_time'] / self._stats['jobs_completed']
                    )
            
            # Notify subscribers
            self._notify_completion_subscribers(notification)
            
            logger.info(f"Job {job_id} completed with status {completion_info['status']} "
                       f"after {duration_seconds} seconds")
            
        except Exception as e:
            logger.error(f"Error handling job completion for {job_id}: {str(e)}")
    
    def _query_job_completion_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Query completion information for a specific job
        
        Args:
            job_id: ID of the job to query
            
        Returns:
            Dictionary with completion information or None if not found
        """
        try:
            with self.db_manager.get_session() as session:
                task = session.query(CaptionGenerationTask).filter_by(id=job_id).first()
                
                if not task:
                    return None
                
                return {
                    'status': task.status.value,
                    'completed_at': task.completed_at.replace(tzinfo=timezone.utc) if task.completed_at else datetime.now(timezone.utc),
                    'error_message': task.error_message
                }
                
        except Exception as e:
            logger.error(f"Error querying job completion info for {job_id}: {str(e)}")
            return None
    
    def _notify_completion_subscribers(self, notification: CompletionNotification) -> None:
        """
        Notify subscribers of job completion
        
        Args:
            notification: Completion notification to send
        """
        with self._callbacks_lock:
            for subscription_id, callback in self._completion_callbacks.items():
                try:
                    callback(notification)
                except Exception as e:
                    logger.error(f"Error in completion callback {subscription_id}: {str(e)}")
    
    def _get_active_job_types(self) -> Dict[str, int]:
        """Get count of active jobs by type"""
        job_types = {}
        for job_info in self._active_jobs.values():
            job_type = job_info.job_type
            job_types[job_type] = job_types.get(job_type, 0) + 1
        return job_types
    
    def _calculate_completion_rate(self) -> float:
        """Calculate job completion rate (completed / total)"""
        with self._stats_lock:
            total_jobs = (self._stats['jobs_completed'] + 
                         self._stats['jobs_failed'] + 
                         self._stats['jobs_cancelled'])
            if total_jobs > 0:
                return self._stats['jobs_completed'] / total_jobs
            return 0.0
    
    def get_job_completion_estimate(self, job_id: str) -> Optional[datetime]:
        """
        Get estimated completion time for a specific job
        
        Args:
            job_id: ID of the job to estimate
            
        Returns:
            Estimated completion datetime or None if not available
        """
        with self._jobs_lock:
            job_info = self._active_jobs.get(job_id)
            if job_info:
                return job_info.estimated_completion
        return None
    
    def get_jobs_by_user(self, user_id: int) -> List[ActiveJobInfo]:
        """
        Get active jobs for a specific user
        
        Args:
            user_id: User ID to filter by
            
        Returns:
            List of ActiveJobInfo objects for the user
        """
        with self._jobs_lock:
            return [job for job in self._active_jobs.values() if job.user_id == user_id]
    
    def get_jobs_by_platform(self, platform_connection_id: int) -> List[ActiveJobInfo]:
        """
        Get active jobs for a specific platform connection
        
        Args:
            platform_connection_id: Platform connection ID to filter by
            
        Returns:
            List of ActiveJobInfo objects for the platform
        """
        with self._jobs_lock:
            return [job for job in self._active_jobs.values() 
                   if job.platform_connection_id == platform_connection_id]
    
    def is_user_job_active(self, user_id: int) -> bool:
        """
        Check if a user has any active jobs
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user has active jobs, False otherwise
        """
        return len(self.get_jobs_by_user(user_id)) > 0
    
    def get_longest_running_job(self) -> Optional[ActiveJobInfo]:
        """
        Get the longest running active job
        
        Returns:
            ActiveJobInfo for longest running job or None if no active jobs
        """
        with self._jobs_lock:
            if not self._active_jobs:
                return None
            
            return min(self._active_jobs.values(), 
                      key=lambda job: job.started_at)
    
    def get_estimated_completion_time(self) -> Optional[datetime]:
        """
        Get estimated completion time for all active jobs
        
        Returns:
            Latest estimated completion time or None if no estimates available
        """
        with self._jobs_lock:
            estimates = [job.estimated_completion for job in self._active_jobs.values() 
                        if job.estimated_completion]
            
            if estimates:
                return max(estimates)  # Return the latest completion estimate
        
        return None
    
    def cleanup_old_completions(self, hours: int = 24) -> int:
        """
        Clean up old completion notifications
        
        Args:
            hours: Age in hours after which to remove completions
            
        Returns:
            Number of completions removed
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            with self._jobs_lock:
                original_count = len(self._completed_jobs)
                self._completed_jobs = [
                    completion for completion in self._completed_jobs
                    if completion.completed_at > cutoff_time
                ]
                removed_count = original_count - len(self._completed_jobs)
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old completion notifications")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old completions: {str(e)}")
            return 0
    
    def __del__(self):
        """Cleanup when tracker is destroyed"""
        try:
            self.stop_monitoring()
        except:
            pass
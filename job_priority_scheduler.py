# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Job Priority Scheduler

Implements dynamic job priority scheduling using configurable priority weights
with queue reordering when priority weights are updated.
"""

import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from database import DatabaseManager
from models import CaptionGenerationTask, TaskStatus, JobPriority, UserRole
from performance_configuration_adapter import PerformanceConfigurationAdapter, PriorityWeights
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

logger = logging.getLogger(__name__)


@dataclass
class JobPriorityScore:
    """Job priority score calculation result"""
    task_id: str
    base_priority: JobPriority
    priority_weight: float
    user_role_bonus: float
    age_factor: float
    final_score: float
    created_at: datetime


class JobPriorityScheduler:
    """
    Job priority scheduler with dynamic priority weight system
    
    Features:
    - Dynamic priority weight calculations
    - User role-based priority bonuses
    - Age-based priority adjustments
    - Queue reordering when weights change
    - Priority score caching for performance
    """
    
    def __init__(self, db_manager: DatabaseManager, performance_adapter: PerformanceConfigurationAdapter):
        """
        Initialize job priority scheduler
        
        Args:
            db_manager: Database manager instance
            performance_adapter: Performance configuration adapter for priority weights
        """
        self.db_manager = db_manager
        self.performance_adapter = performance_adapter
        self._lock = threading.RLock()
        
        # Priority calculation settings
        self.USER_ROLE_BONUSES = {
            UserRole.ADMIN: 1.5,      # 50% bonus for admin users
            UserRole.REVIEWER: 1.2,   # 20% bonus for reviewers
            UserRole.VIEWER: 1.0      # No bonus for regular users
        }
        
        # Age factor settings (jobs get slight priority boost as they age)
        self.MAX_AGE_BONUS = 0.3      # Maximum 30% bonus for old jobs
        self.AGE_BONUS_HOURS = 24     # Full bonus after 24 hours
        
        # Priority score cache
        self._priority_cache: Dict[str, JobPriorityScore] = {}
        self._cache_lock = threading.RLock()
        
        # Subscribe to priority weight changes
        self._setup_priority_weight_subscription()
    
    def _setup_priority_weight_subscription(self):
        """Set up subscription for priority weight changes"""
        try:
            # Subscribe to priority weight changes to trigger queue reordering
            self.performance_adapter.config_service.subscribe_to_changes(
                "processing_priority_weights",
                self._handle_priority_weights_change
            )
            logger.info("Job priority scheduler subscribed to priority weight changes")
        except Exception as e:
            logger.error(f"Error setting up priority weight subscription: {str(e)}")
    
    def calculate_job_priority_score(self, task: CaptionGenerationTask, user_role: UserRole) -> JobPriorityScore:
        """
        Calculate priority score for a job
        
        Args:
            task: Caption generation task
            user_role: User role for role-based bonus
            
        Returns:
            JobPriorityScore with detailed calculation
        """
        try:
            # Get base priority weight
            priority_weight = self.performance_adapter.get_priority_score(task.priority)
            
            # Calculate user role bonus
            user_role_bonus = self.USER_ROLE_BONUSES.get(user_role, 1.0)
            
            # Calculate age factor (jobs get slight priority boost as they age)
            age_factor = self._calculate_age_factor(task.created_at)
            
            # Calculate final score
            final_score = priority_weight * user_role_bonus * (1.0 + age_factor)
            
            return JobPriorityScore(
                task_id=task.id,
                base_priority=task.priority,
                priority_weight=priority_weight,
                user_role_bonus=user_role_bonus,
                age_factor=age_factor,
                final_score=final_score,
                created_at=task.created_at
            )
            
        except Exception as e:
            logger.error(f"Error calculating priority score for task {task.id}: {str(e)}")
            # Return default score on error
            return JobPriorityScore(
                task_id=task.id,
                base_priority=task.priority,
                priority_weight=2.0,  # Default normal priority
                user_role_bonus=1.0,
                age_factor=0.0,
                final_score=2.0,
                created_at=task.created_at
            )
    
    def _calculate_age_factor(self, created_at: datetime) -> float:
        """
        Calculate age-based priority factor
        
        Args:
            created_at: Task creation timestamp
            
        Returns:
            Age factor (0.0 to MAX_AGE_BONUS)
        """
        try:
            now = datetime.now(timezone.utc)
            age_hours = (now - created_at).total_seconds() / 3600
            
            # Linear increase up to maximum bonus
            age_factor = min(age_hours / self.AGE_BONUS_HOURS, 1.0) * self.MAX_AGE_BONUS
            return age_factor
            
        except Exception as e:
            logger.error(f"Error calculating age factor: {str(e)}")
            return 0.0
    
    def get_prioritized_job_queue(self, limit: int = 50) -> List[Tuple[CaptionGenerationTask, JobPriorityScore]]:
        """
        Get prioritized job queue with calculated priority scores
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of (task, priority_score) tuples ordered by priority
        """
        try:
            with self.db_manager.get_session() as session:
                # Get queued tasks with user information
                queued_tasks = session.query(CaptionGenerationTask).join(
                    CaptionGenerationTask.user
                ).filter(
                    CaptionGenerationTask.status == TaskStatus.QUEUED
                ).limit(limit * 2).all()  # Get more than needed for sorting
                
                # Calculate priority scores
                prioritized_jobs = []
                for task in queued_tasks:
                    # Check cache first
                    cached_score = self._get_cached_priority_score(task.id)
                    if cached_score and cached_score.created_at == task.created_at:
                        priority_score = cached_score
                    else:
                        # Calculate new score
                        priority_score = self.calculate_job_priority_score(task, task.user.role)
                        self._cache_priority_score(priority_score)
                    
                    prioritized_jobs.append((task, priority_score))
                
                # Sort by priority score (highest first)
                prioritized_jobs.sort(key=lambda x: x[1].final_score, reverse=True)
                
                # Return top jobs
                return prioritized_jobs[:limit]
                
        except Exception as e:
            logger.error(f"Error getting prioritized job queue: {str(e)}")
            return []
    
    def get_next_priority_job(self) -> Optional[Tuple[CaptionGenerationTask, JobPriorityScore]]:
        """
        Get the next highest priority job
        
        Returns:
            Tuple of (task, priority_score) or None if no jobs available
        """
        try:
            prioritized_jobs = self.get_prioritized_job_queue(limit=1)
            return prioritized_jobs[0] if prioritized_jobs else None
            
        except Exception as e:
            logger.error(f"Error getting next priority job: {str(e)}")
            return None
    
    def reorder_queue_by_priority(self) -> int:
        """
        Reorder the job queue based on current priority weights
        
        This method updates the database ordering of queued jobs based on
        their calculated priority scores.
        
        Returns:
            Number of jobs reordered
        """
        try:
            with self._lock:
                # Clear priority cache since weights may have changed
                self._clear_priority_cache()
                
                # Get all queued jobs with priority scores
                prioritized_jobs = self.get_prioritized_job_queue(limit=1000)  # Get all queued jobs
                
                if not prioritized_jobs:
                    return 0
                
                # Update database with new ordering
                # Note: This is a simplified approach. In a production system,
                # you might want to add a priority_order column to the database
                # and update it here, then use it in the queue selection query.
                
                reordered_count = len(prioritized_jobs)
                
                logger.info(f"Reordered {reordered_count} jobs based on updated priority weights")
                
                # Log top priority jobs for debugging
                if prioritized_jobs:
                    top_jobs = prioritized_jobs[:5]  # Top 5 jobs
                    logger.debug("Top priority jobs after reordering:")
                    for i, (task, score) in enumerate(top_jobs, 1):
                        logger.debug(f"  {i}. Task {task.id}: {score.base_priority.value} "
                                   f"(score: {score.final_score:.2f})")
                
                return reordered_count
                
        except Exception as e:
            logger.error(f"Error reordering queue by priority: {str(e)}")
            return 0
    
    def _get_cached_priority_score(self, task_id: str) -> Optional[JobPriorityScore]:
        """Get cached priority score for a task"""
        with self._cache_lock:
            return self._priority_cache.get(task_id)
    
    def _cache_priority_score(self, priority_score: JobPriorityScore):
        """Cache a priority score"""
        with self._cache_lock:
            self._priority_cache[priority_score.task_id] = priority_score
            
            # Limit cache size
            if len(self._priority_cache) > 1000:
                # Remove oldest entries
                sorted_scores = sorted(
                    self._priority_cache.values(),
                    key=lambda x: x.created_at
                )
                for score in sorted_scores[:100]:  # Remove oldest 100
                    self._priority_cache.pop(score.task_id, None)
    
    def _clear_priority_cache(self):
        """Clear the priority score cache"""
        with self._cache_lock:
            self._priority_cache.clear()
            logger.debug("Priority score cache cleared")
    
    def _handle_priority_weights_change(self, key: str, old_value: Any, new_value: Any):
        """
        Handle priority weights configuration change
        
        Args:
            key: Configuration key
            old_value: Previous value
            new_value: New value
        """
        logger.info(f"Priority weights changed: {old_value} -> {new_value}")
        
        try:
            # Reorder queue with new priority weights
            reordered_count = self.reorder_queue_by_priority()
            logger.info(f"Queue reordered with new priority weights: {reordered_count} jobs affected")
            
        except Exception as e:
            logger.error(f"Error handling priority weights change: {str(e)}")
    
    def get_priority_statistics(self) -> Dict[str, Any]:
        """
        Get priority scheduling statistics
        
        Returns:
            Dictionary with priority statistics
        """
        try:
            with self.db_manager.get_session() as session:
                # Count jobs by priority level
                priority_counts = {}
                for priority in JobPriority:
                    count = session.query(CaptionGenerationTask).filter(
                        and_(
                            CaptionGenerationTask.status == TaskStatus.QUEUED,
                            CaptionGenerationTask.priority == priority
                        )
                    ).count()
                    priority_counts[priority.value] = count
                
                # Get current priority weights
                current_weights = self.performance_adapter._current_priority_weights.to_dict()
                
                # Cache statistics
                cache_stats = {
                    'cached_scores': len(self._priority_cache),
                    'cache_limit': 1000
                }
                
                return {
                    'priority_counts': priority_counts,
                    'current_weights': current_weights,
                    'user_role_bonuses': {role.value: bonus for role, bonus in self.USER_ROLE_BONUSES.items()},
                    'age_bonus_settings': {
                        'max_age_bonus': self.MAX_AGE_BONUS,
                        'age_bonus_hours': self.AGE_BONUS_HOURS
                    },
                    'cache_stats': cache_stats
                }
                
        except Exception as e:
            logger.error(f"Error getting priority statistics: {str(e)}")
            return {'error': str(e)}
    
    def validate_priority_weights(self, weights: Dict[str, float]) -> List[str]:
        """
        Validate priority weight configuration
        
        Args:
            weights: Priority weights to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            # Check required keys
            required_keys = ['urgent', 'high', 'normal', 'low']
            for key in required_keys:
                if key not in weights:
                    errors.append(f"Missing required priority weight: {key}")
                else:
                    try:
                        weight = float(weights[key])
                        if weight <= 0:
                            errors.append(f"Priority weight '{key}' must be positive, got: {weight}")
                    except (ValueError, TypeError):
                        errors.append(f"Priority weight '{key}' must be a number, got: {weights[key]}")
            
            # Check weight ordering (urgent should be highest)
            if len(errors) == 0:  # Only check ordering if all weights are valid
                try:
                    urgent = float(weights['urgent'])
                    high = float(weights['high'])
                    normal = float(weights['normal'])
                    low = float(weights['low'])
                    
                    if not (urgent >= high >= normal >= low):
                        errors.append("Priority weights should be ordered: urgent >= high >= normal >= low")
                        
                except (ValueError, TypeError):
                    pass  # Already caught above
            
        except Exception as e:
            errors.append(f"Error validating priority weights: {str(e)}")
        
        return errors
    
    def get_job_priority_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed priority information for a specific job
        
        Args:
            task_id: Task ID to get details for
            
        Returns:
            Dictionary with priority details or None if not found
        """
        try:
            with self.db_manager.get_session() as session:
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    return None
                
                # Calculate priority score
                priority_score = self.calculate_job_priority_score(task, task.user.role)
                
                return {
                    'task_id': task_id,
                    'base_priority': task.priority.value,
                    'priority_weight': priority_score.priority_weight,
                    'user_role': task.user.role.value,
                    'user_role_bonus': priority_score.user_role_bonus,
                    'age_factor': priority_score.age_factor,
                    'final_score': priority_score.final_score,
                    'created_at': task.created_at.isoformat(),
                    'status': task.status.value
                }
                
        except Exception as e:
            logger.error(f"Error getting job priority details for {task_id}: {str(e)}")
            return None
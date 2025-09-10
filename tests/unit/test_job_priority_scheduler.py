# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Job Priority Scheduler

Tests dynamic job priority scheduling using configurable priority weights
with queue reordering when priority weights are updated.
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.task.scheduling.job_priority_scheduler import (
    JobPriorityScheduler,
    JobPriorityScore
)
from models import JobPriority, UserRole, TaskStatus
from performance_configuration_adapter import PriorityWeights


class TestJobPriorityScore(unittest.TestCase):
    """Test JobPriorityScore data class"""
    
    def test_job_priority_score_creation(self):
        """Test creating JobPriorityScore"""
        created_at = datetime.now(timezone.utc)
        score = JobPriorityScore(
            task_id="test-task-123",
            base_priority=JobPriority.HIGH,
            priority_weight=3.0,
            user_role_bonus=1.2,
            age_factor=0.1,
            final_score=3.96,
            created_at=created_at
        )
        
        self.assertEqual(score.task_id, "test-task-123")
        self.assertEqual(score.base_priority, JobPriority.HIGH)
        self.assertEqual(score.priority_weight, 3.0)
        self.assertEqual(score.user_role_bonus, 1.2)
        self.assertEqual(score.age_factor, 0.1)
        self.assertEqual(score.final_score, 3.96)
        self.assertEqual(score.created_at, created_at)


class TestJobPriorityScheduler(unittest.TestCase):
    """Test JobPriorityScheduler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.mock_performance_adapter = Mock()
        
        # Mock priority weights
        self.mock_priority_weights = PriorityWeights(urgent=4.0, high=3.0, normal=2.0, low=1.0)
        self.mock_performance_adapter._current_priority_weights = self.mock_priority_weights
        self.mock_performance_adapter.get_priority_score.side_effect = self._mock_get_priority_score
        
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_performance_adapter.config_service = self.mock_config_service
        
        self.scheduler = JobPriorityScheduler(self.mock_db_manager, self.mock_performance_adapter)
    
    def _mock_get_priority_score(self, priority: JobPriority) -> float:
        """Mock priority score lookup"""
        priority_map = {
            JobPriority.URGENT: 4.0,
            JobPriority.HIGH: 3.0,
            JobPriority.NORMAL: 2.0,
            JobPriority.LOW: 1.0
        }
        return priority_map.get(priority, 2.0)
    
    def _create_mock_task(self, task_id: str, priority: JobPriority, user_role: UserRole, 
                         created_at: datetime = None) -> Mock:
        """Create a mock task for testing"""
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        
        task = Mock()
        task.id = task_id
        task.priority = priority
        task.created_at = created_at
        task.status = TaskStatus.QUEUED
        
        # Mock user
        user = Mock()
        user.role = user_role
        task.user = user
        
        return task
    
    def test_initialization(self):
        """Test scheduler initialization"""
        self.assertIsNotNone(self.scheduler)
        self.assertEqual(self.scheduler.db_manager, self.mock_db_manager)
        self.assertEqual(self.scheduler.performance_adapter, self.mock_performance_adapter)
        
        # Verify subscription was set up
        self.mock_config_service.subscribe_to_changes.assert_called_once()
    
    def test_calculate_job_priority_score_basic(self):
        """Test basic priority score calculation"""
        task = self._create_mock_task("test-task", JobPriority.HIGH, UserRole.VIEWER)
        
        score = self.scheduler.calculate_job_priority_score(task, UserRole.VIEWER)
        
        self.assertEqual(score.task_id, "test-task")
        self.assertEqual(score.base_priority, JobPriority.HIGH)
        self.assertEqual(score.priority_weight, 3.0)
        self.assertEqual(score.user_role_bonus, 1.0)  # No bonus for regular user
        self.assertEqual(score.age_factor, 0.0)  # New task, no age bonus
        self.assertEqual(score.final_score, 3.0)  # 3.0 * 1.0 * (1.0 + 0.0)
    
    def test_calculate_job_priority_score_with_admin_bonus(self):
        """Test priority score calculation with admin user bonus"""
        task = self._create_mock_task("admin-task", JobPriority.NORMAL, UserRole.ADMIN)
        
        score = self.scheduler.calculate_job_priority_score(task, UserRole.ADMIN)
        
        self.assertEqual(score.base_priority, JobPriority.NORMAL)
        self.assertEqual(score.priority_weight, 2.0)
        self.assertEqual(score.user_role_bonus, 1.5)  # 50% bonus for admin
        self.assertEqual(score.final_score, 3.0)  # 2.0 * 1.5 * (1.0 + 0.0)
    
    def test_calculate_job_priority_score_with_reviewer_bonus(self):
        """Test priority score calculation with reviewer user bonus"""
        task = self._create_mock_task("reviewer-task", JobPriority.HIGH, UserRole.REVIEWER)
        
        score = self.scheduler.calculate_job_priority_score(task, UserRole.REVIEWER)
        
        self.assertEqual(score.base_priority, JobPriority.HIGH)
        self.assertEqual(score.priority_weight, 3.0)
        self.assertEqual(score.user_role_bonus, 1.2)  # 20% bonus for reviewer
        self.assertEqual(score.final_score, 3.6)  # 3.0 * 1.2 * (1.0 + 0.0)
    
    def test_calculate_job_priority_score_with_age_factor(self):
        """Test priority score calculation with age factor"""
        # Create task that's 12 hours old (should get 50% of max age bonus)
        old_time = datetime.now(timezone.utc) - timedelta(hours=12)
        task = self._create_mock_task("old-task", JobPriority.NORMAL, UserRole.VIEWER, old_time)
        
        score = self.scheduler.calculate_job_priority_score(task, UserRole.VIEWER)
        
        self.assertEqual(score.base_priority, JobPriority.NORMAL)
        self.assertEqual(score.priority_weight, 2.0)
        self.assertEqual(score.user_role_bonus, 1.0)
        self.assertAlmostEqual(score.age_factor, 0.15, places=2)  # 50% of 0.3 max bonus
        self.assertAlmostEqual(score.final_score, 2.3, places=1)  # 2.0 * 1.0 * (1.0 + 0.15)
    
    def test_calculate_age_factor(self):
        """Test age factor calculation"""
        # Test new task (0 hours old)
        now = datetime.now(timezone.utc)
        age_factor = self.scheduler._calculate_age_factor(now)
        self.assertEqual(age_factor, 0.0)
        
        # Test 12-hour old task (50% of max bonus)
        twelve_hours_ago = now - timedelta(hours=12)
        age_factor = self.scheduler._calculate_age_factor(twelve_hours_ago)
        self.assertAlmostEqual(age_factor, 0.15, places=2)  # 50% of 0.3
        
        # Test 24-hour old task (full bonus)
        twenty_four_hours_ago = now - timedelta(hours=24)
        age_factor = self.scheduler._calculate_age_factor(twenty_four_hours_ago)
        self.assertAlmostEqual(age_factor, 0.3, places=2)
        
        # Test 48-hour old task (capped at max bonus)
        forty_eight_hours_ago = now - timedelta(hours=48)
        age_factor = self.scheduler._calculate_age_factor(forty_eight_hours_ago)
        self.assertAlmostEqual(age_factor, 0.3, places=2)  # Capped at max
    
    def test_get_prioritized_job_queue(self):
        """Test getting prioritized job queue"""
        # Create mock tasks with different priorities
        tasks = [
            self._create_mock_task("low-task", JobPriority.LOW, UserRole.VIEWER),
            self._create_mock_task("urgent-task", JobPriority.URGENT, UserRole.VIEWER),
            self._create_mock_task("normal-task", JobPriority.NORMAL, UserRole.VIEWER),
            self._create_mock_task("high-task", JobPriority.HIGH, UserRole.VIEWER)
        ]
        
        # Mock database session and query
        mock_session = Mock()
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = tasks
        mock_session.query.return_value = mock_query
        
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        # Get prioritized queue
        prioritized_jobs = self.scheduler.get_prioritized_job_queue(limit=10)
        
        # Should be ordered by priority score (highest first)
        self.assertEqual(len(prioritized_jobs), 4)
        
        # Check ordering: URGENT (4.0) > HIGH (3.0) > NORMAL (2.0) > LOW (1.0)
        task_ids = [job[0].id for job in prioritized_jobs]
        expected_order = ["urgent-task", "high-task", "normal-task", "low-task"]
        self.assertEqual(task_ids, expected_order)
    
    def test_get_next_priority_job(self):
        """Test getting next highest priority job"""
        # Create mock task
        urgent_task = self._create_mock_task("urgent-task", JobPriority.URGENT, UserRole.ADMIN)
        
        # Mock the get_prioritized_job_queue method
        mock_score = JobPriorityScore(
            task_id="urgent-task",
            base_priority=JobPriority.URGENT,
            priority_weight=4.0,
            user_role_bonus=1.5,
            age_factor=0.0,
            final_score=6.0,
            created_at=urgent_task.created_at
        )
        
        with patch.object(self.scheduler, 'get_prioritized_job_queue') as mock_get_queue:
            mock_get_queue.return_value = [(urgent_task, mock_score)]
            
            result = self.scheduler.get_next_priority_job()
            
            self.assertIsNotNone(result)
            task, score = result
            self.assertEqual(task.id, "urgent-task")
            self.assertEqual(score.final_score, 6.0)
    
    def test_get_next_priority_job_empty_queue(self):
        """Test getting next priority job when queue is empty"""
        with patch.object(self.scheduler, 'get_prioritized_job_queue') as mock_get_queue:
            mock_get_queue.return_value = []
            
            result = self.scheduler.get_next_priority_job()
            
            self.assertIsNone(result)
    
    def test_reorder_queue_by_priority(self):
        """Test queue reordering by priority"""
        # Create mock tasks
        tasks = [
            self._create_mock_task("task1", JobPriority.LOW, UserRole.VIEWER),
            self._create_mock_task("task2", JobPriority.URGENT, UserRole.ADMIN)
        ]
        
        # Mock prioritized jobs
        mock_scores = [
            JobPriorityScore("task2", JobPriority.URGENT, 4.0, 1.5, 0.0, 6.0, datetime.now(timezone.utc)),
            JobPriorityScore("task1", JobPriority.LOW, 1.0, 1.0, 0.0, 1.0, datetime.now(timezone.utc))
        ]
        
        prioritized_jobs = list(zip(tasks, mock_scores))
        
        with patch.object(self.scheduler, 'get_prioritized_job_queue') as mock_get_queue:
            mock_get_queue.return_value = prioritized_jobs
            
            result = self.scheduler.reorder_queue_by_priority()
            
            self.assertEqual(result, 2)  # 2 jobs reordered
    
    def test_priority_weights_change_handler(self):
        """Test handling priority weights change"""
        old_weights = {"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        new_weights = {"urgent": 5.0, "high": 4.0, "normal": 2.0, "low": 0.5}
        
        with patch.object(self.scheduler, 'reorder_queue_by_priority') as mock_reorder:
            mock_reorder.return_value = 5
            
            self.scheduler._handle_priority_weights_change(
                "processing_priority_weights", old_weights, new_weights
            )
            
            mock_reorder.assert_called_once()
    
    def test_validate_priority_weights_valid(self):
        """Test validation of valid priority weights"""
        valid_weights = {"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        
        errors = self.scheduler.validate_priority_weights(valid_weights)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_priority_weights_missing_keys(self):
        """Test validation with missing keys"""
        invalid_weights = {"urgent": 4.0, "high": 3.0}  # Missing normal and low
        
        errors = self.scheduler.validate_priority_weights(invalid_weights)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Missing required priority weight: normal" in error for error in errors))
        self.assertTrue(any("Missing required priority weight: low" in error for error in errors))
    
    def test_validate_priority_weights_negative_values(self):
        """Test validation with negative values"""
        invalid_weights = {"urgent": -1.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        
        errors = self.scheduler.validate_priority_weights(invalid_weights)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("must be positive" in error for error in errors))
    
    def test_validate_priority_weights_wrong_order(self):
        """Test validation with wrong priority order"""
        invalid_weights = {"urgent": 1.0, "high": 4.0, "normal": 3.0, "low": 2.0}  # Wrong order
        
        errors = self.scheduler.validate_priority_weights(invalid_weights)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("should be ordered" in error for error in errors))
    
    def test_get_priority_statistics(self):
        """Test getting priority statistics"""
        # Mock database session and queries
        mock_session = Mock()
        mock_query = Mock()
        
        # Mock priority counts
        priority_counts = {
            JobPriority.URGENT: 2,
            JobPriority.HIGH: 5,
            JobPriority.NORMAL: 10,
            JobPriority.LOW: 3
        }
        
        def mock_count_side_effect(*args, **kwargs):
            # Extract priority from the filter call
            # This is a simplified mock - in reality you'd need more sophisticated mocking
            return 5  # Default count
        
        mock_query.filter.return_value = mock_query
        mock_query.count.side_effect = mock_count_side_effect
        mock_session.query.return_value = mock_query
        
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        # Add some cached scores
        self.scheduler._priority_cache = {
            "task1": Mock(),
            "task2": Mock(),
            "task3": Mock()
        }
        
        stats = self.scheduler.get_priority_statistics()
        
        self.assertIn('priority_counts', stats)
        self.assertIn('current_weights', stats)
        self.assertIn('user_role_bonuses', stats)
        self.assertIn('age_bonus_settings', stats)
        self.assertIn('cache_stats', stats)
        
        # Check cache stats
        self.assertEqual(stats['cache_stats']['cached_scores'], 3)
    
    def test_get_job_priority_details(self):
        """Test getting detailed priority information for a job"""
        task = self._create_mock_task("detail-task", JobPriority.HIGH, UserRole.REVIEWER)
        
        # Mock database session
        mock_session = Mock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = task
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        details = self.scheduler.get_job_priority_details("detail-task")
        
        self.assertIsNotNone(details)
        self.assertEqual(details['task_id'], "detail-task")
        self.assertEqual(details['base_priority'], JobPriority.HIGH.value)
        self.assertEqual(details['priority_weight'], 3.0)
        self.assertEqual(details['user_role'], UserRole.REVIEWER.value)
        self.assertEqual(details['user_role_bonus'], 1.2)
        self.assertIn('final_score', details)
        self.assertIn('created_at', details)
    
    def test_get_job_priority_details_not_found(self):
        """Test getting priority details for non-existent job"""
        # Mock database session returning None
        mock_session = Mock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        details = self.scheduler.get_job_priority_details("nonexistent-task")
        
        self.assertIsNone(details)
    
    def test_priority_cache_operations(self):
        """Test priority score caching operations"""
        # Test caching
        score = JobPriorityScore(
            task_id="cache-test",
            base_priority=JobPriority.NORMAL,
            priority_weight=2.0,
            user_role_bonus=1.0,
            age_factor=0.0,
            final_score=2.0,
            created_at=datetime.now(timezone.utc)
        )
        
        self.scheduler._cache_priority_score(score)
        
        # Test retrieval
        cached_score = self.scheduler._get_cached_priority_score("cache-test")
        self.assertIsNotNone(cached_score)
        self.assertEqual(cached_score.task_id, "cache-test")
        
        # Test cache clearing
        self.scheduler._clear_priority_cache()
        cached_score = self.scheduler._get_cached_priority_score("cache-test")
        self.assertIsNone(cached_score)


class TestJobPrioritySchedulerIntegration(unittest.TestCase):
    """Integration tests for job priority scheduler"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_db_manager = Mock()
        self.mock_performance_adapter = Mock()
        
        # Mock priority weights
        self.mock_priority_weights = PriorityWeights(urgent=5.0, high=3.0, normal=2.0, low=1.0)
        self.mock_performance_adapter._current_priority_weights = self.mock_priority_weights
        self.mock_performance_adapter.get_priority_score.side_effect = self._mock_get_priority_score
        
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_performance_adapter.config_service = self.mock_config_service
    
    def _mock_get_priority_score(self, priority: JobPriority) -> float:
        """Mock priority score lookup"""
        priority_map = {
            JobPriority.URGENT: 5.0,
            JobPriority.HIGH: 3.0,
            JobPriority.NORMAL: 2.0,
            JobPriority.LOW: 1.0
        }
        return priority_map.get(priority, 2.0)
    
    def test_complete_priority_calculation_workflow(self):
        """Test complete priority calculation workflow"""
        scheduler = JobPriorityScheduler(self.mock_db_manager, self.mock_performance_adapter)
        
        # Create tasks with different characteristics
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=12)
        
        # High priority admin task (should score highest)
        admin_task = Mock()
        admin_task.id = "admin-high"
        admin_task.priority = JobPriority.HIGH
        admin_task.created_at = now
        admin_task.user = Mock()
        admin_task.user.role = UserRole.ADMIN
        
        # Urgent regular user task (high base priority)
        urgent_task = Mock()
        urgent_task.id = "user-urgent"
        urgent_task.priority = JobPriority.URGENT
        urgent_task.created_at = now
        urgent_task.user = Mock()
        urgent_task.user.role = UserRole.VIEWER
        
        # Old normal task (gets age bonus)
        old_task = Mock()
        old_task.id = "old-normal"
        old_task.priority = JobPriority.NORMAL
        old_task.created_at = old_time
        old_task.user = Mock()
        old_task.user.role = UserRole.VIEWER
        
        # Calculate scores
        admin_score = scheduler.calculate_job_priority_score(admin_task, UserRole.ADMIN)
        urgent_score = scheduler.calculate_job_priority_score(urgent_task, UserRole.VIEWER)
        old_score = scheduler.calculate_job_priority_score(old_task, UserRole.VIEWER)
        
        # Verify score calculations
        # Admin high: 3.0 * 1.5 * 1.0 = 4.5
        self.assertAlmostEqual(admin_score.final_score, 4.5, places=1)
        
        # User urgent: 5.0 * 1.0 * 1.0 = 5.0
        self.assertAlmostEqual(urgent_score.final_score, 5.0, places=1)
        
        # Old normal: 2.0 * 1.0 * (1.0 + 0.15) = 2.3
        self.assertAlmostEqual(old_score.final_score, 2.3, places=1)
        
        # Verify ordering: urgent_task > admin_task > old_task
        scores = [urgent_score, admin_score, old_score]
        scores.sort(key=lambda x: x.final_score, reverse=True)
        
        expected_order = ["user-urgent", "admin-high", "old-normal"]
        actual_order = [score.task_id for score in scores]
        self.assertEqual(actual_order, expected_order)


if __name__ == '__main__':
    unittest.main()
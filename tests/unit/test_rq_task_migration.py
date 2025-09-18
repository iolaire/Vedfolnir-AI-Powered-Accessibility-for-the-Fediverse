# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for RQ Task Migration and Fallback Mechanisms

Tests the migration of tasks between database and RQ systems, fallback mechanisms
for Redis unavailability, and hybrid processing support during transitions.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import redis
from rq import Queue, Job
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import SQLAlchemyError

from app.core.database.core.database_manager import DatabaseManager
from app.services.task.migration.task_migration_manager import TaskMigrationManager
from app.services.task.rq.redis_fallback_manager import RedisFallbackManager
from app.services.task.rq.redis_health_monitor import RedisHealthMonitor
from app.services.task.rq.rq_queue_manager import RQQueueManager
from app.services.task.core.task_queue_manager import TaskQueueManager
from models import CaptionGenerationTask, TaskStatus, JobPriority, User, UserRole


class TestTaskMigrationManager(unittest.TestCase):
    """Test Task Migration Manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.mock_rq_queue_manager = Mock(spec=RQQueueManager)
        
        # Initialize migration manager
        self.migration_manager = TaskMigrationManager(
            self.mock_db_manager,
            self.mock_rq_queue_manager
        )
    
    def test_initialization(self):
        """Test TaskMigrationManager initialization"""
        # Verify initialization
        self.assertEqual(self.migration_manager.db_manager, self.mock_db_manager)
        self.assertEqual(self.migration_manager.rq_queue_manager, self.mock_rq_queue_manager)
        self.assertIsInstance(self.migration_manager.migration_stats, dict)
    
    def test_migrate_database_tasks_to_rq_success(self):
        """Test successful migration of database tasks to RQ"""
        # Mock database tasks
        mock_tasks = []
        for i in range(3):
            task = Mock(spec=CaptionGenerationTask)
            task.id = f"db-task-{i}"
            task.user_id = i + 1
            task.platform_connection_id = 1
            task.status = TaskStatus.QUEUED
            task.priority = JobPriority.NORMAL
            task.created_at = datetime.now(timezone.utc)
            task.settings = None
            mock_tasks.append(task)
        
        # Mock database query
        self.mock_session.query.return_value.filter_by.return_value.all.return_value = mock_tasks
        
        # Mock RQ enqueue success
        self.mock_rq_queue_manager.enqueue_task.side_effect = [
            "rq-task-0", "rq-task-1", "rq-task-2"
        ]
        
        # Test migration
        result = self.migration_manager.migrate_database_tasks_to_rq()
        
        # Verify migration results
        self.assertTrue(result['success'])
        self.assertEqual(result['migrated_count'], 3)
        self.assertEqual(result['failed_count'], 0)
        self.assertEqual(len(result['failed_tasks']), 0)
        
        # Verify RQ enqueue was called for each task
        self.assertEqual(self.mock_rq_queue_manager.enqueue_task.call_count, 3)
        
        # Verify database tasks were updated
        for task in mock_tasks:
            self.assertEqual(task.status, TaskStatus.QUEUED)  # Should remain queued in DB for tracking
    
    def test_migrate_database_tasks_to_rq_partial_failure(self):
        """Test migration with some tasks failing"""
        # Mock database tasks
        mock_tasks = []
        for i in range(3):
            task = Mock(spec=CaptionGenerationTask)
            task.id = f"db-task-{i}"
            task.user_id = i + 1
            task.platform_connection_id = 1
            task.status = TaskStatus.QUEUED
            task.priority = JobPriority.NORMAL
            task.created_at = datetime.now(timezone.utc)
            task.settings = None
            mock_tasks.append(task)
        
        self.mock_session.query.return_value.filter_by.return_value.all.return_value = mock_tasks
        
        # Mock RQ enqueue with one failure
        self.mock_rq_queue_manager.enqueue_task.side_effect = [
            "rq-task-0", 
            Exception("Redis connection failed"), 
            "rq-task-2"
        ]
        
        # Test migration
        result = self.migration_manager.migrate_database_tasks_to_rq()
        
        # Verify partial migration results
        self.assertFalse(result['success'])  # Not fully successful
        self.assertEqual(result['migrated_count'], 2)
        self.assertEqual(result['failed_count'], 1)
        self.assertEqual(len(result['failed_tasks']), 1)
        self.assertEqual(result['failed_tasks'][0]['task_id'], 'db-task-1')
    
    def test_migrate_rq_tasks_to_database(self):
        """Test migration of RQ tasks back to database"""
        # Mock RQ tasks
        mock_rq_tasks = [
            {'task_id': 'rq-task-1', 'user_id': 1, 'priority': 'normal'},
            {'task_id': 'rq-task-2', 'user_id': 2, 'priority': 'high'},
        ]
        
        # Mock RQ queue manager methods
        self.mock_rq_queue_manager.get_all_queued_tasks.return_value = mock_rq_tasks
        self.mock_rq_queue_manager.remove_task_from_queue.return_value = True
        
        # Mock database task creation
        mock_db_tasks = []
        for task_data in mock_rq_tasks:
            db_task = Mock(spec=CaptionGenerationTask)
            db_task.id = task_data['task_id']
            db_task.user_id = task_data['user_id']
            mock_db_tasks.append(db_task)
        
        # Test migration
        result = self.migration_manager.migrate_rq_tasks_to_database()
        
        # Verify migration results
        self.assertTrue(result['success'])
        self.assertEqual(result['migrated_count'], 2)
        self.assertEqual(result['failed_count'], 0)
        
        # Verify database operations
        self.assertEqual(self.mock_session.add.call_count, 2)
        self.mock_session.commit.assert_called()
    
    def test_validate_migration_data_integrity(self):
        """Test validation of migration data integrity"""
        # Mock tasks in both systems
        db_tasks = [
            {'id': 'task-1', 'user_id': 1, 'status': 'queued'},
            {'id': 'task-2', 'user_id': 2, 'status': 'running'},
        ]
        
        rq_tasks = [
            {'task_id': 'task-1', 'user_id': 1, 'status': 'queued'},
            {'task_id': 'task-3', 'user_id': 3, 'status': 'queued'},  # Extra task in RQ
        ]
        
        # Mock data retrieval
        self.mock_session.query.return_value.all.return_value = [
            Mock(id='task-1', user_id=1, status=TaskStatus.QUEUED),
            Mock(id='task-2', user_id=2, status=TaskStatus.RUNNING)
        ]
        
        self.mock_rq_queue_manager.get_all_tasks.return_value = rq_tasks
        
        # Test validation
        validation_result = self.migration_manager.validate_migration_data_integrity()
        
        # Verify validation results
        self.assertIn('db_only_tasks', validation_result)
        self.assertIn('rq_only_tasks', validation_result)
        self.assertIn('common_tasks', validation_result)
        self.assertIn('data_integrity_issues', validation_result)
        
        # Verify specific findings
        self.assertEqual(len(validation_result['db_only_tasks']), 1)  # task-2
        self.assertEqual(len(validation_result['rq_only_tasks']), 1)   # task-3
        self.assertEqual(len(validation_result['common_tasks']), 1)    # task-1
    
    def test_rollback_migration(self):
        """Test rollback of migration operations"""
        # Mock migration history
        migration_id = "migration-123"
        self.migration_manager.migration_history[migration_id] = {
            'type': 'db_to_rq',
            'migrated_tasks': ['task-1', 'task-2'],
            'timestamp': datetime.now(timezone.utc),
            'status': 'completed'
        }
        
        # Mock rollback operations
        self.mock_rq_queue_manager.remove_task_from_queue.return_value = True
        
        # Test rollback
        result = self.migration_manager.rollback_migration(migration_id)
        
        # Verify rollback results
        self.assertTrue(result['success'])
        self.assertEqual(result['rollback_count'], 2)
        
        # Verify RQ tasks were removed
        self.assertEqual(self.mock_rq_queue_manager.remove_task_from_queue.call_count, 2)
    
    def test_hybrid_processing_support(self):
        """Test hybrid processing during migration transition"""
        # Mock active tasks in both systems
        db_task = Mock(spec=CaptionGenerationTask)
        db_task.id = "db-task-1"
        db_task.user_id = 1
        db_task.status = TaskStatus.RUNNING
        
        rq_task_data = {'task_id': 'rq-task-1', 'user_id': 2, 'status': 'running'}
        
        # Mock system queries
        self.mock_session.query.return_value.filter.return_value.all.return_value = [db_task]
        self.mock_rq_queue_manager.get_running_tasks.return_value = [rq_task_data]
        
        # Test hybrid status check
        hybrid_status = self.migration_manager.get_hybrid_processing_status()
        
        # Verify hybrid status
        self.assertIn('db_active_tasks', hybrid_status)
        self.assertIn('rq_active_tasks', hybrid_status)
        self.assertIn('total_active_tasks', hybrid_status)
        self.assertIn('processing_mode', hybrid_status)
        
        self.assertEqual(len(hybrid_status['db_active_tasks']), 1)
        self.assertEqual(len(hybrid_status['rq_active_tasks']), 1)
        self.assertEqual(hybrid_status['total_active_tasks'], 2)
        self.assertEqual(hybrid_status['processing_mode'], 'hybrid')
    
    def test_migration_performance_tracking(self):
        """Test migration performance tracking"""
        # Start migration tracking
        migration_id = self.migration_manager.start_migration_tracking('db_to_rq')
        
        # Simulate migration operations
        self.migration_manager.track_migration_progress(migration_id, 'migrating', 5, 0)
        self.migration_manager.track_migration_progress(migration_id, 'completed', 10, 1)
        
        # Get migration statistics
        stats = self.migration_manager.get_migration_statistics(migration_id)
        
        # Verify statistics
        self.assertIn('migration_id', stats)
        self.assertIn('type', stats)
        self.assertIn('status', stats)
        self.assertIn('migrated_count', stats)
        self.assertIn('failed_count', stats)
        self.assertIn('duration', stats)
        
        self.assertEqual(stats['status'], 'completed')
        self.assertEqual(stats['migrated_count'], 10)
        self.assertEqual(stats['failed_count'], 1)


class TestRedisFallbackManager(unittest.TestCase):
    """Test Redis Fallback Manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_task_queue_manager = Mock(spec=TaskQueueManager)
        
        # Initialize fallback manager
        self.fallback_manager = RedisFallbackManager(
            self.mock_db_manager,
            self.mock_redis,
            self.mock_task_queue_manager
        )
    
    def test_initialization(self):
        """Test RedisFallbackManager initialization"""
        # Verify initialization
        self.assertEqual(self.fallback_manager.db_manager, self.mock_db_manager)
        self.assertEqual(self.fallback_manager.redis_connection, self.mock_redis)
        self.assertEqual(self.fallback_manager.task_queue_manager, self.mock_task_queue_manager)
        self.assertFalse(self.fallback_manager.fallback_mode_active)
    
    def test_detect_redis_failure(self):
        """Test Redis failure detection"""
        # Mock Redis ping failure
        self.mock_redis.ping.side_effect = redis.ConnectionError("Connection failed")
        
        # Test failure detection
        is_healthy = self.fallback_manager.check_redis_health()
        
        # Verify failure detection
        self.assertFalse(is_healthy)
        self.assertTrue(self.fallback_manager.fallback_mode_active)
    
    def test_activate_fallback_mode(self):
        """Test activation of fallback mode"""
        # Test fallback activation
        self.fallback_manager.activate_fallback_mode("Redis connection timeout")
        
        # Verify fallback mode is active
        self.assertTrue(self.fallback_manager.fallback_mode_active)
        self.assertIsNotNone(self.fallback_manager.fallback_activated_at)
        self.assertEqual(self.fallback_manager.fallback_reason, "Redis connection timeout")
    
    def test_deactivate_fallback_mode(self):
        """Test deactivation of fallback mode"""
        # Activate fallback first
        self.fallback_manager.activate_fallback_mode("Test reason")
        
        # Mock Redis recovery
        self.mock_redis.ping.return_value = True
        
        # Test fallback deactivation
        self.fallback_manager.deactivate_fallback_mode()
        
        # Verify fallback mode is deactivated
        self.assertFalse(self.fallback_manager.fallback_mode_active)
        self.assertIsNotNone(self.fallback_manager.fallback_deactivated_at)
    
    def test_enqueue_task_fallback_mode(self):
        """Test task enqueuing in fallback mode"""
        # Activate fallback mode
        self.fallback_manager.activate_fallback_mode("Redis unavailable")
        
        # Create test task
        task = CaptionGenerationTask(
            id="fallback-task-123",
            user_id=1,
            platform_connection_id=1,
            status=TaskStatus.QUEUED
        )
        
        # Mock database enqueue
        self.mock_task_queue_manager.enqueue_task.return_value = "fallback-task-123"
        
        # Test enqueuing in fallback mode
        result = self.fallback_manager.enqueue_task_with_fallback(task)
        
        # Verify task was enqueued to database
        self.assertEqual(result, "fallback-task-123")
        self.mock_task_queue_manager.enqueue_task.assert_called_once_with(task)
    
    def test_automatic_redis_recovery_detection(self):
        """Test automatic Redis recovery detection"""
        # Activate fallback mode
        self.fallback_manager.activate_fallback_mode("Redis failure")
        
        # Mock Redis recovery
        self.mock_redis.ping.return_value = True
        
        # Test recovery detection
        recovery_detected = self.fallback_manager.check_for_redis_recovery()
        
        # Verify recovery was detected
        self.assertTrue(recovery_detected)
        self.assertFalse(self.fallback_manager.fallback_mode_active)
    
    def test_fallback_statistics_tracking(self):
        """Test fallback statistics tracking"""
        # Activate and use fallback mode
        self.fallback_manager.activate_fallback_mode("Test failure")
        
        # Simulate fallback operations
        for i in range(5):
            task = CaptionGenerationTask(id=f"task-{i}", user_id=1, platform_connection_id=1)
            self.mock_task_queue_manager.enqueue_task.return_value = f"task-{i}"
            self.fallback_manager.enqueue_task_with_fallback(task)
        
        # Get fallback statistics
        stats = self.fallback_manager.get_fallback_statistics()
        
        # Verify statistics
        self.assertIn('fallback_mode_active', stats)
        self.assertIn('fallback_activations', stats)
        self.assertIn('tasks_processed_in_fallback', stats)
        self.assertIn('current_fallback_duration', stats)
        
        self.assertTrue(stats['fallback_mode_active'])
        self.assertEqual(stats['tasks_processed_in_fallback'], 5)


class TestRedisHealthMonitor(unittest.TestCase):
    """Test Redis Health Monitor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock Redis connection
        self.mock_redis = Mock(spec=redis.Redis)
        
        # Initialize health monitor
        self.health_monitor = RedisHealthMonitor(self.mock_redis)
    
    def test_initialization(self):
        """Test RedisHealthMonitor initialization"""
        # Verify initialization
        self.assertEqual(self.health_monitor.redis_connection, self.mock_redis)
        self.assertEqual(self.health_monitor.health_check_interval, 30)
        self.assertEqual(self.health_monitor.failure_threshold, 3)
        self.assertEqual(self.health_monitor.consecutive_failures, 0)
        self.assertTrue(self.health_monitor.is_healthy)
    
    def test_health_check_success(self):
        """Test successful health check"""
        # Mock successful Redis operations
        self.mock_redis.ping.return_value = True
        self.mock_redis.info.return_value = {'used_memory': 1024 * 1024 * 50}  # 50 MB
        
        # Test health check
        is_healthy = self.health_monitor.check_health()
        
        # Verify health check passed
        self.assertTrue(is_healthy)
        self.assertEqual(self.health_monitor.consecutive_failures, 0)
        self.assertTrue(self.health_monitor.is_healthy)
    
    def test_health_check_failure(self):
        """Test health check failure"""
        # Mock Redis connection failure
        self.mock_redis.ping.side_effect = redis.ConnectionError("Connection failed")
        
        # Test health check failure
        is_healthy = self.health_monitor.check_health()
        
        # Verify health check failed
        self.assertFalse(is_healthy)
        self.assertEqual(self.health_monitor.consecutive_failures, 1)
    
    def test_failure_threshold_exceeded(self):
        """Test behavior when failure threshold is exceeded"""
        # Mock Redis failures
        self.mock_redis.ping.side_effect = redis.ConnectionError("Connection failed")
        
        # Trigger multiple failures
        for i in range(4):  # Exceed threshold of 3
            self.health_monitor.check_health()
        
        # Verify failure handling
        self.assertEqual(self.health_monitor.consecutive_failures, 4)
        self.assertFalse(self.health_monitor.is_healthy)
    
    def test_memory_usage_monitoring(self):
        """Test Redis memory usage monitoring"""
        # Mock Redis memory info
        self.mock_redis.info.return_value = {
            'used_memory': 1024 * 1024 * 800,  # 800 MB
            'maxmemory': 1024 * 1024 * 1024    # 1 GB
        }
        
        # Test memory monitoring
        memory_status = self.health_monitor.get_memory_usage()
        
        # Verify memory status
        self.assertIn('used_memory_mb', memory_status)
        self.assertIn('max_memory_mb', memory_status)
        self.assertIn('usage_percentage', memory_status)
        self.assertIn('memory_warning', memory_status)
        
        self.assertEqual(memory_status['used_memory_mb'], 800.0)
        self.assertEqual(memory_status['usage_percentage'], 80.0)
        self.assertTrue(memory_status['memory_warning'])  # Over 75% threshold
    
    def test_recovery_detection(self):
        """Test Redis recovery detection"""
        # Simulate failure state
        self.health_monitor.consecutive_failures = 3
        self.health_monitor.is_healthy = False
        
        # Mock Redis recovery
        self.mock_redis.ping.return_value = True
        self.mock_redis.info.return_value = {'used_memory': 1024 * 1024 * 50}
        
        # Test recovery detection
        is_healthy = self.health_monitor.check_health()
        
        # Verify recovery
        self.assertTrue(is_healthy)
        self.assertEqual(self.health_monitor.consecutive_failures, 0)
        self.assertTrue(self.health_monitor.is_healthy)
    
    def test_health_status_reporting(self):
        """Test comprehensive health status reporting"""
        # Mock Redis info
        self.mock_redis.ping.return_value = True
        self.mock_redis.info.return_value = {
            'used_memory': 1024 * 1024 * 100,
            'maxmemory': 1024 * 1024 * 1024,
            'connected_clients': 5,
            'total_commands_processed': 1000
        }
        
        # Get health status
        status = self.health_monitor.get_health_status()
        
        # Verify status structure
        self.assertIn('is_healthy', status)
        self.assertIn('consecutive_failures', status)
        self.assertIn('last_check_time', status)
        self.assertIn('memory_usage', status)
        self.assertIn('connection_info', status)
        
        # Verify specific values
        self.assertTrue(status['is_healthy'])
        self.assertEqual(status['consecutive_failures'], 0)
        self.assertIn('used_memory_mb', status['memory_usage'])
        self.assertIn('connected_clients', status['connection_info'])


class TestTaskMigrationIntegration(unittest.TestCase):
    """Integration tests for task migration components"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        # Mock all dependencies for integration testing
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_rq_queue_manager = Mock(spec=RQQueueManager)
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_task_queue_manager = Mock(spec=TaskQueueManager)
        
        # Initialize all components
        self.migration_manager = TaskMigrationManager(
            self.mock_db_manager,
            self.mock_rq_queue_manager
        )
        
        self.fallback_manager = RedisFallbackManager(
            self.mock_db_manager,
            self.mock_redis,
            self.mock_task_queue_manager
        )
        
        self.health_monitor = RedisHealthMonitor(self.mock_redis)
    
    def test_complete_migration_workflow(self):
        """Test complete migration workflow from database to RQ"""
        # Mock database tasks
        mock_session = Mock()
        self.mock_db_manager.get_session.return_value = mock_session
        
        db_tasks = [
            Mock(id='task-1', user_id=1, status=TaskStatus.QUEUED),
            Mock(id='task-2', user_id=2, status=TaskStatus.QUEUED)
        ]
        mock_session.query.return_value.filter_by.return_value.all.return_value = db_tasks
        
        # Mock successful RQ enqueue
        self.mock_rq_queue_manager.enqueue_task.side_effect = ['rq-task-1', 'rq-task-2']
        
        # Execute migration
        migration_result = self.migration_manager.migrate_database_tasks_to_rq()
        
        # Verify migration success
        self.assertTrue(migration_result['success'])
        self.assertEqual(migration_result['migrated_count'], 2)
        
        # Verify data integrity
        validation_result = self.migration_manager.validate_migration_data_integrity()
        self.assertIsInstance(validation_result, dict)
    
    def test_redis_failure_and_recovery_workflow(self):
        """Test Redis failure detection and recovery workflow"""
        # Initial healthy state
        self.mock_redis.ping.return_value = True
        self.assertTrue(self.health_monitor.check_health())
        
        # Simulate Redis failure
        self.mock_redis.ping.side_effect = redis.ConnectionError("Connection lost")
        
        # Health check should detect failure
        self.assertFalse(self.health_monitor.check_health())
        
        # Fallback manager should activate fallback mode
        self.fallback_manager.activate_fallback_mode("Redis connection lost")
        self.assertTrue(self.fallback_manager.fallback_mode_active)
        
        # Simulate Redis recovery
        self.mock_redis.ping.side_effect = None
        self.mock_redis.ping.return_value = True
        
        # Health check should detect recovery
        self.assertTrue(self.health_monitor.check_health())
        
        # Fallback manager should detect recovery
        recovery_detected = self.fallback_manager.check_for_redis_recovery()
        self.assertTrue(recovery_detected)
        self.assertFalse(self.fallback_manager.fallback_mode_active)


if __name__ == '__main__':
    unittest.main()
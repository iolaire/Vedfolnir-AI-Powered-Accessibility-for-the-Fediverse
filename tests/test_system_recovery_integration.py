# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration Tests for System Recovery

Tests all recovery scenarios including startup recovery, graceful shutdown,
database connection recovery, AI service outage detection, concurrent operation
handling, and job state recovery.
"""

import unittest
import asyncio
import threading
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

# Test imports
from config import Config
from database import DatabaseManager
from models import CaptionGenerationTask, TaskStatus, User, UserRole, PlatformConnection, JobPriority
from task_queue_manager import TaskQueueManager
from progress_tracker import ProgressTracker

# Recovery components
from system_recovery_manager import SystemRecoveryManager, initialize_system_recovery
from graceful_shutdown_handler import GracefulShutdownHandler, initialize_graceful_shutdown
from database_connection_recovery import DatabaseConnectionRecovery
from ai_service_monitor import AIServiceMonitor, ServiceStatus
from concurrent_operation_manager import ConcurrentOperationManager, OperationType, LockScope

class TestSystemRecoveryIntegration(unittest.TestCase):
    """Integration tests for system recovery components"""
    
    def setUp(self):
        """Set up test environment"""
        # Create test configuration
        self.config = Config()
        
        # Use in-memory database for testing - bypass MySQL validation
        self.config.storage.database_url = "sqlite:///:memory:"
        
        # Initialize database manager with SQLite support
        from database import DatabaseManager
        import os
        
        # Temporarily override environment to allow SQLite for testing
        original_db_type = os.environ.get('DB_TYPE')
        os.environ['DB_TYPE'] = 'sqlite'
        
        try:
            self.db_manager = DatabaseManager(self.config)
        finally:
            # Restore original environment
            if original_db_type:
                os.environ['DB_TYPE'] = original_db_type
            else:
                os.environ.pop('DB_TYPE', None)
        
        # Create tables
        from models import Base
        Base.metadata.create_all(self.db_manager.engine)
        
        # Initialize components
        self.task_queue_manager = TaskQueueManager(self.db_manager)
        self.progress_tracker = ProgressTracker(self.db_manager)
        
        # Initialize recovery components
        self.recovery_manager = SystemRecoveryManager(
            self.db_manager, self.task_queue_manager, self.progress_tracker
        )
        
        self.db_recovery = DatabaseConnectionRecovery(self.db_manager)
        
        self.ai_monitor = AIServiceMonitor(
            self.db_manager, self.task_queue_manager, self.progress_tracker
        )
        
        self.operation_manager = ConcurrentOperationManager(self.db_manager)
        
        # Create test data
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        # Shutdown components
        if hasattr(self.ai_monitor, 'stop_monitoring'):
            self.ai_monitor.stop_monitoring()
        
        if hasattr(self.operation_manager, 'shutdown'):
            self.operation_manager.shutdown()
        
        # Close database connections
        if hasattr(self.db_manager, 'dispose_engine'):
            self.db_manager.dispose_engine()
    
    def _create_test_data(self):
        """Create test data for recovery scenarios"""
        with self.db_manager.get_session() as session:
            # Create test user
            self.test_user = User(
                username="test_user",
                email="test@example.com",
                role=UserRole.REVIEWER,
                is_active=True
            )
            self.test_user.set_password("test_password")
            session.add(self.test_user)
            session.flush()
            
            # Create test platform connection
            self.test_platform = PlatformConnection(
                user_id=self.test_user.id,
                name="Test Platform",
                platform_type="mastodon",
                instance_url="https://test.example.com",
                is_active=True
            )
            session.add(self.test_platform)
            session.flush()
            
            # Store IDs for later use
            self.test_user_id = self.test_user.id
            self.test_platform_id = self.test_platform.id
            
            session.commit()
    
    def test_startup_recovery_with_interrupted_tasks(self):
        """Test startup recovery handles interrupted tasks correctly"""
        # Create interrupted tasks
        interrupted_tasks = []
        with self.db_manager.get_session() as session:
            for i in range(3):
                task = CaptionGenerationTask(
                    user_id=self.test_user_id,
                    platform_connection_id=self.test_platform_id,
                    status=TaskStatus.RUNNING,
                    started_at=datetime.now(timezone.utc) - timedelta(minutes=30),
                    retry_count=i
                )
                session.add(task)
                interrupted_tasks.append(task.id)
            session.commit()
        
        # Run startup recovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            recovery_stats = loop.run_until_complete(
                self.recovery_manager.startup_recovery()
            )
            
            # Verify recovery statistics
            self.assertEqual(recovery_stats['interrupted_tasks_found'], 3)
            self.assertGreaterEqual(recovery_stats['tasks_recovered'], 0)
            self.assertGreaterEqual(recovery_stats['recovery_time_seconds'], 0)
            
            # Verify task states after recovery
            with self.db_manager.get_session() as session:
                for task_id in interrupted_tasks:
                    task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                    self.assertIsNotNone(task)
                    # Task should be either queued for retry or failed
                    self.assertIn(task.status, [TaskStatus.QUEUED, TaskStatus.FAILED])
                    
        finally:
            loop.close()
    
    def test_graceful_shutdown_with_active_tasks(self):
        """Test graceful shutdown handles active tasks correctly"""
        # Create active tasks
        active_tasks = []
        with self.db_manager.get_session() as session:
            # Create queued task
            queued_task = CaptionGenerationTask(
                user_id=self.test_user_id,
                platform_connection_id=self.test_platform_id,
                status=TaskStatus.QUEUED
            )
            session.add(queued_task)
            active_tasks.append(queued_task.id)
            
            # Create running task
            running_task = CaptionGenerationTask(
                user_id=self.test_user_id,
                platform_connection_id=self.test_platform_id,
                status=TaskStatus.RUNNING,
                started_at=datetime.now(timezone.utc)
            )
            session.add(running_task)
            active_tasks.append(running_task.id)
            
            session.commit()
        
        # Run graceful shutdown with short timeout
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            shutdown_stats = loop.run_until_complete(
                self.recovery_manager.graceful_shutdown(timeout_seconds=2)
            )
            
            # Verify shutdown statistics
            self.assertEqual(shutdown_stats['active_tasks_found'], 2)
            self.assertGreaterEqual(shutdown_stats['tasks_cancelled'], 0)
            self.assertGreaterEqual(shutdown_stats['shutdown_time_seconds'], 0)
            
            # Verify tasks were handled
            with self.db_manager.get_session() as session:
                for task_id in active_tasks:
                    task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                    self.assertIsNotNone(task)
                    # Tasks should be completed or cancelled
                    self.assertIn(task.status, [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED])
                    
        finally:
            loop.close()
    
    def test_database_connection_recovery(self):
        """Test database connection recovery functionality"""
        # Test connection health check
        healthy = self.db_recovery.test_connection()
        self.assertTrue(healthy)
        
        # Test recovery when connection is healthy
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            recovery_success = loop.run_until_complete(
                self.db_recovery.recover_connection()
            )
            self.assertTrue(recovery_success)
            
            # Test resilient session context manager
            with self.db_recovery.resilient_session() as session:
                # Perform database operation
                user_count = session.query(User).count()
                self.assertGreaterEqual(user_count, 1)
            
            # Test connection health status
            health_status = self.db_recovery.get_connection_health()
            self.assertIsInstance(health_status, dict)
            self.assertIn('healthy', health_status)
            
        finally:
            loop.close()
    
    @patch('ollama_caption_generator.OllamaCaptionGenerator')
    def test_ai_service_outage_detection(self, mock_generator_class):
        """Test AI service outage detection and handling"""
        # Mock AI service
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        # Test service available
        mock_generator.test_connection.return_value = asyncio.coroutine(lambda: True)()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Test health check when service is available
            available = loop.run_until_complete(
                self.ai_monitor.detect_ai_service_outage()
            )
            self.assertTrue(available)
            
            # Test service unavailable
            mock_generator.test_connection.return_value = asyncio.coroutine(lambda: False)()
            
            # Create running task to be failed
            with self.db_manager.get_session() as session:
                running_task = CaptionGenerationTask(
                    user_id=self.test_user_id,
                    platform_connection_id=self.test_platform_id,
                    status=TaskStatus.RUNNING,
                    started_at=datetime.now(timezone.utc)
                )
                session.add(running_task)
                session.commit()
                task_id = running_task.id
            
            # Test outage detection
            available = loop.run_until_complete(
                self.ai_monitor.detect_ai_service_outage()
            )
            self.assertFalse(available)
            
            # Verify running task was failed
            with self.db_manager.get_session() as session:
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                self.assertEqual(task.status, TaskStatus.FAILED)
                self.assertIn("AI service", task.error_message)
            
            # Test service status
            status = self.ai_monitor.get_service_status()
            self.assertIsInstance(status, dict)
            self.assertIn('status', status)
            
        finally:
            loop.close()
    
    def test_concurrent_operation_handling(self):
        """Test concurrent operation handling and conflict prevention"""
        # Test basic lock acquisition
        with self.operation_manager.acquire_lock(
            OperationType.TASK_CREATION, 
            LockScope.USER, 
            str(self.test_user_id)
        ) as lock:
            self.assertIsNotNone(lock)
            self.assertEqual(lock.operation_type, OperationType.TASK_CREATION)
            self.assertEqual(lock.resource_id, str(self.test_user_id))
        
        # Test lock conflict detection
        def acquire_conflicting_lock():
            try:
                with self.operation_manager.acquire_lock(
                    OperationType.TASK_CREATION,
                    LockScope.USER,
                    str(self.test_user_id),
                    timeout=1
                ):
                    time.sleep(2)  # Hold lock longer than timeout
            except RuntimeError:
                pass  # Expected conflict
        
        # Start first operation
        thread1 = threading.Thread(target=acquire_conflicting_lock)
        thread1.start()
        
        time.sleep(0.1)  # Let first thread acquire lock
        
        # Try to acquire conflicting lock
        with self.assertRaises(RuntimeError):
            with self.operation_manager.acquire_lock(
                OperationType.TASK_CREATION,
                LockScope.USER,
                str(self.test_user_id),
                timeout=1
            ):
                pass
        
        thread1.join()
        
        # Test lock statistics
        stats = self.operation_manager.get_lock_statistics()
        self.assertIsInstance(stats, dict)
        self.assertIn('active_locks', stats)
        self.assertIn('total_operations', stats)
    
    def test_job_state_recovery(self):
        """Test job state recovery after system restarts"""
        # Create task in running state (simulating interrupted job)
        with self.db_manager.get_session() as session:
            task = CaptionGenerationTask(
                user_id=self.test_user_id,
                platform_connection_id=self.test_platform_id,
                status=TaskStatus.RUNNING,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                retry_count=1
            )
            session.add(task)
            session.commit()
            task_id = task.id
        
        # Test job state recovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            recovery_success = loop.run_until_complete(
                self.recovery_manager.recover_job_state(task_id)
            )
            self.assertTrue(recovery_success)
            
            # Verify task state after recovery
            with self.db_manager.get_session() as session:
                recovered_task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                self.assertIsNotNone(recovered_task)
                # Task should be queued for retry
                self.assertEqual(recovered_task.status, TaskStatus.QUEUED)
                self.assertEqual(recovered_task.retry_count, 2)
                
        finally:
            loop.close()
    
    def test_stuck_task_recovery(self):
        """Test recovery of stuck tasks (running too long)"""
        # Create stuck task (running for over 1 hour)
        with self.db_manager.get_session() as session:
            stuck_task = CaptionGenerationTask(
                user_id=self.test_user_id,
                platform_connection_id=self.test_platform_id,
                status=TaskStatus.RUNNING,
                started_at=datetime.now(timezone.utc) - timedelta(hours=2),
                retry_count=0
            )
            session.add(stuck_task)
            session.commit()
            task_id = stuck_task.id
        
        # Test stuck task recovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            recovery_success = loop.run_until_complete(
                self.recovery_manager.recover_job_state(task_id)
            )
            self.assertTrue(recovery_success)
            
            # Verify stuck task was marked as failed
            with self.db_manager.get_session() as session:
                recovered_task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                self.assertIsNotNone(recovered_task)
                self.assertEqual(recovered_task.status, TaskStatus.FAILED)
                self.assertIn("stuck", recovered_task.error_message.lower())
                
        finally:
            loop.close()
    
    def test_max_retry_recovery(self):
        """Test recovery of tasks that have exceeded max retries"""
        # Create task with max retries exceeded
        with self.db_manager.get_session() as session:
            max_retry_task = CaptionGenerationTask(
                user_id=self.test_user_id,
                platform_connection_id=self.test_platform_id,
                status=TaskStatus.RUNNING,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                retry_count=3,
                max_retries=3
            )
            session.add(max_retry_task)
            session.commit()
            task_id = max_retry_task.id
        
        # Test recovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            recovery_success = loop.run_until_complete(
                self.recovery_manager.recover_job_state(task_id)
            )
            self.assertTrue(recovery_success)
            
            # Verify task was marked as failed (no more retries)
            with self.db_manager.get_session() as session:
                recovered_task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                self.assertIsNotNone(recovered_task)
                self.assertEqual(recovered_task.status, TaskStatus.FAILED)
                self.assertIn("retries", recovered_task.error_message.lower())
                
        finally:
            loop.close()
    
    def test_recovery_callbacks(self):
        """Test recovery callback system"""
        callback_calls = []
        
        def test_callback(event_type, data=None):
            callback_calls.append((event_type, data))
        
        # Register callbacks
        self.recovery_manager.register_startup_callback(lambda: test_callback("startup"))
        self.recovery_manager.register_shutdown_callback(lambda: test_callback("shutdown"))
        self.recovery_manager.register_recovery_callback(test_callback)
        
        # Test startup callbacks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.recovery_manager.startup_recovery())
            
            # Verify startup callback was called
            startup_calls = [call for call in callback_calls if call[0] == "startup"]
            self.assertGreater(len(startup_calls), 0)
            
            # Test shutdown callbacks
            loop.run_until_complete(self.recovery_manager.graceful_shutdown(timeout_seconds=1))
            
            # Verify shutdown callback was called
            shutdown_calls = [call for call in callback_calls if call[0] == "shutdown"]
            self.assertGreater(len(shutdown_calls), 0)
            
        finally:
            loop.close()
    
    def test_comprehensive_recovery_scenario(self):
        """Test comprehensive recovery scenario with multiple components"""
        # Create complex scenario with multiple issues
        with self.db_manager.get_session() as session:
            # Running task (should be recovered)
            running_task = CaptionGenerationTask(
                user_id=self.test_user_id,
                platform_connection_id=self.test_platform_id,
                status=TaskStatus.RUNNING,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=10)
            )
            session.add(running_task)
            
            # Stuck task (should be failed)
            stuck_task = CaptionGenerationTask(
                user_id=self.test_user_id,
                platform_connection_id=self.test_platform_id,
                status=TaskStatus.RUNNING,
                started_at=datetime.now(timezone.utc) - timedelta(hours=2)
            )
            session.add(stuck_task)
            
            # Queued task (should remain queued)
            queued_task = CaptionGenerationTask(
                user_id=self.test_user_id,
                platform_connection_id=self.test_platform_id,
                status=TaskStatus.QUEUED
            )
            session.add(queued_task)
            
            session.commit()
            
            running_task_id = running_task.id
            stuck_task_id = stuck_task.id
            queued_task_id = queued_task.id
        
        # Run comprehensive recovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Test startup recovery
            recovery_stats = loop.run_until_complete(
                self.recovery_manager.startup_recovery()
            )
            
            # Verify recovery handled all scenarios correctly
            self.assertGreaterEqual(recovery_stats['interrupted_tasks_found'], 2)
            
            # Check individual task states
            with self.db_manager.get_session() as session:
                # Running task should be queued for retry
                running_recovered = session.query(CaptionGenerationTask).filter_by(id=running_task_id).first()
                self.assertEqual(running_recovered.status, TaskStatus.QUEUED)
                
                # Stuck task should be failed
                stuck_recovered = session.query(CaptionGenerationTask).filter_by(id=stuck_task_id).first()
                self.assertEqual(stuck_recovered.status, TaskStatus.FAILED)
                
                # Queued task should remain queued
                queued_recovered = session.query(CaptionGenerationTask).filter_by(id=queued_task_id).first()
                self.assertEqual(queued_recovered.status, TaskStatus.QUEUED)
            
            # Test graceful shutdown
            shutdown_stats = loop.run_until_complete(
                self.recovery_manager.graceful_shutdown(timeout_seconds=2)
            )
            
            # Verify shutdown handled remaining tasks
            self.assertGreaterEqual(shutdown_stats['active_tasks_found'], 0)
            
        finally:
            loop.close()

if __name__ == '__main__':
    unittest.main()
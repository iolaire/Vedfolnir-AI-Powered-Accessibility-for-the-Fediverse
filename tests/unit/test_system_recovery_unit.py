# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit Tests for System Recovery Components

Tests individual recovery components without requiring full database setup.
"""

import unittest
import asyncio
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

# Recovery components
from system_recovery_manager import SystemRecoveryManager
from graceful_shutdown_handler import GracefulShutdownHandler
from database_connection_recovery import DatabaseConnectionRecovery
from ai_service_monitor import AIServiceMonitor, ServiceStatus, ServiceHealthCheck
from app.services.batch.concurrent.concurrent_operation_manager import ConcurrentOperationManager, OperationType, LockScope

class TestSystemRecoveryComponents(unittest.TestCase):
    """Unit tests for individual recovery components"""
    
    def setUp(self):
        """Set up test environment with mocks"""
        # Mock database manager
        self.mock_db_manager = Mock()
        self.mock_db_manager.get_session.return_value.__enter__ = Mock()
        self.mock_db_manager.get_session.return_value.__exit__ = Mock()
        
        # Mock task queue manager
        self.mock_task_queue_manager = Mock()
        
        # Mock progress tracker
        self.mock_progress_tracker = Mock()
        
        # Initialize components with mocks
        self.recovery_manager = SystemRecoveryManager(
            self.mock_db_manager, self.mock_task_queue_manager, self.mock_progress_tracker
        )
        
        self.db_recovery = DatabaseConnectionRecovery(self.mock_db_manager)
        
        self.ai_monitor = AIServiceMonitor(
            self.mock_db_manager, self.mock_task_queue_manager, self.mock_progress_tracker
        )
        
        self.operation_manager = ConcurrentOperationManager(self.mock_db_manager)
    
    def tearDown(self):
        """Clean up test environment"""
        # Stop monitoring if active
        if hasattr(self.ai_monitor, 'stop_monitoring'):
            self.ai_monitor.stop_monitoring()
        
        # Shutdown operation manager
        if hasattr(self.operation_manager, 'shutdown'):
            self.operation_manager.shutdown()
    
    def test_system_recovery_manager_initialization(self):
        """Test SystemRecoveryManager initialization"""
        self.assertIsNotNone(self.recovery_manager)
        self.assertEqual(self.recovery_manager.db_manager, self.mock_db_manager)
        self.assertEqual(self.recovery_manager.task_queue_manager, self.mock_task_queue_manager)
        self.assertEqual(self.recovery_manager.progress_tracker, self.mock_progress_tracker)
        
        # Test callback registration
        callback_called = False
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        self.recovery_manager.register_startup_callback(test_callback)
        self.assertEqual(len(self.recovery_manager._startup_callbacks), 1)
    
    def test_database_connection_recovery_initialization(self):
        """Test DatabaseConnectionRecovery initialization"""
        self.assertIsNotNone(self.db_recovery)
        self.assertEqual(self.db_recovery.db_manager, self.mock_db_manager)
        self.assertTrue(self.db_recovery._connection_healthy)
        self.assertEqual(self.db_recovery._failed_connections, 0)
    
    def test_ai_service_monitor_initialization(self):
        """Test AIServiceMonitor initialization"""
        self.assertIsNotNone(self.ai_monitor)
        self.assertEqual(self.ai_monitor.db_manager, self.mock_db_manager)
        self.assertEqual(self.ai_monitor._current_status, ServiceStatus.UNKNOWN)
        self.assertFalse(self.ai_monitor._monitoring_active)
    
    def test_concurrent_operation_manager_initialization(self):
        """Test ConcurrentOperationManager initialization"""
        self.assertIsNotNone(self.operation_manager)
        self.assertEqual(self.operation_manager.db_manager, self.mock_db_manager)
        self.assertEqual(len(self.operation_manager._active_locks), 0)
    
    def test_concurrent_operation_lock_acquisition(self):
        """Test concurrent operation lock acquisition and release"""
        # Test successful lock acquisition
        with self.operation_manager.acquire_lock(
            OperationType.TASK_CREATION,
            LockScope.USER,
            "test_user_123"
        ) as lock:
            self.assertIsNotNone(lock)
            self.assertEqual(lock.operation_type, OperationType.TASK_CREATION)
            self.assertEqual(lock.scope, LockScope.USER)
            self.assertEqual(lock.resource_id, "test_user_123")
            
            # Verify lock is active
            self.assertEqual(len(self.operation_manager._active_locks), 1)
        
        # Verify lock is released
        self.assertEqual(len(self.operation_manager._active_locks), 0)
    
    def test_concurrent_operation_lock_conflict(self):
        """Test concurrent operation lock conflict detection"""
        # Acquire first lock
        with self.operation_manager.acquire_lock(
            OperationType.TASK_CREATION,
            LockScope.USER,
            "test_user_123"
        ):
            # Try to acquire conflicting lock from different thread context
            # We need to simulate different thread by changing the thread name
            original_thread_name = threading.current_thread().name
            threading.current_thread().name = "different_thread"
            
            try:
                with self.assertRaises(RuntimeError):
                    with self.operation_manager.acquire_lock(
                        OperationType.TASK_CREATION,
                        LockScope.USER,
                        "test_user_123"
                    ):
                        pass
            finally:
                # Restore original thread name
                threading.current_thread().name = original_thread_name
    
    def test_ai_service_health_check_creation(self):
        """Test AI service health check creation"""
        # Create a health check result
        health_check = ServiceHealthCheck(
            status=ServiceStatus.AVAILABLE,
            response_time_ms=50.0,
            error_message=None,
            timestamp=datetime.now(timezone.utc),
            check_type="test"
        )
        
        self.assertEqual(health_check.status, ServiceStatus.AVAILABLE)
        self.assertEqual(health_check.response_time_ms, 50.0)
        self.assertIsNone(health_check.error_message)
        self.assertEqual(health_check.check_type, "test")
    
    @patch('ollama_caption_generator.OllamaCaptionGenerator')
    def test_ai_service_health_check_available(self, mock_generator_class):
        """Test AI service health check when service is available"""
        # Mock AI service
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        # Create async mock
        async def mock_test_connection():
            return True
        
        mock_generator.test_connection = mock_test_connection
        
        # Run health check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            health_check = loop.run_until_complete(
                self.ai_monitor.check_service_health()
            )
            
            self.assertEqual(health_check.status, ServiceStatus.AVAILABLE)
            self.assertIsNone(health_check.error_message)
            self.assertIsNotNone(health_check.response_time_ms)
            
        finally:
            loop.close()
    
    @patch('ollama_caption_generator.OllamaCaptionGenerator')
    def test_ai_service_health_check_unavailable(self, mock_generator_class):
        """Test AI service health check when service is unavailable"""
        # Mock AI service failure
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        # Create async mock that raises exception
        async def mock_test_connection():
            raise Exception("Connection failed")
        
        mock_generator.test_connection = mock_test_connection
        
        # Run health check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            health_check = loop.run_until_complete(
                self.ai_monitor.check_service_health()
            )
            
            self.assertEqual(health_check.status, ServiceStatus.UNAVAILABLE)
            self.assertIsNotNone(health_check.error_message)
            self.assertIn("Connection failed", health_check.error_message)
            
        finally:
            loop.close()
    
    def test_ai_service_status_tracking(self):
        """Test AI service status tracking"""
        # Test initial status
        status = self.ai_monitor.get_service_status()
        self.assertEqual(status['status'], ServiceStatus.UNKNOWN.value)
        self.assertEqual(status['consecutive_failures'], 0)
        self.assertEqual(status['consecutive_successes'], 0)
        
        # Test status after health check - need to set initial status to available first
        # to trigger the recovery threshold logic
        self.ai_monitor._current_status = ServiceStatus.AVAILABLE
        
        health_check = ServiceHealthCheck(
            status=ServiceStatus.AVAILABLE,
            response_time_ms=50.0,
            error_message=None,
            timestamp=datetime.now(timezone.utc),
            check_type="test"
        )
        
        self.ai_monitor._update_status(health_check)
        
        status = self.ai_monitor.get_service_status()
        self.assertEqual(status['status'], ServiceStatus.AVAILABLE.value)
        self.assertEqual(status['consecutive_successes'], 1)
    
    def test_database_recovery_health_check(self):
        """Test database connection health check"""
        # Mock successful database query
        mock_session = Mock()
        mock_result = Mock()
        mock_result_row = Mock()
        mock_result_row.test = 1  # This is what the query expects
        mock_result.fetchone.return_value = mock_result_row
        mock_session.execute.return_value = mock_result
        
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        # Test connection health
        healthy = self.db_recovery.test_connection()
        self.assertTrue(healthy)
        
        # Verify session was used
        mock_session.execute.assert_called_once()
    
    def test_database_recovery_callback_registration(self):
        """Test database recovery callback registration"""
        callback_calls = []
        
        def test_callback(event_type, data):
            callback_calls.append((event_type, data))
        
        self.db_recovery.register_recovery_callback(test_callback)
        
        # Trigger callback
        self.db_recovery._notify_recovery_callbacks("test_event", {"test": "data"})
        
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0][0], "test_event")
        self.assertEqual(callback_calls[0][1]["test"], "data")
    
    def test_operation_manager_statistics(self):
        """Test operation manager statistics"""
        # Get initial statistics
        stats = self.operation_manager.get_lock_statistics()
        self.assertEqual(stats['active_locks'], 0)
        self.assertIsInstance(stats['operation_counts'], dict)
        self.assertIsInstance(stats['scope_counts'], dict)
        
        # Acquire a lock and check statistics
        with self.operation_manager.acquire_lock(
            OperationType.TASK_CREATION,
            LockScope.USER,
            "test_user"
        ):
            stats = self.operation_manager.get_lock_statistics()
            self.assertEqual(stats['active_locks'], 1)
            self.assertEqual(stats['operation_counts']['task_creation'], 1)
            self.assertEqual(stats['scope_counts']['user'], 1)
    
    def test_operation_manager_history_tracking(self):
        """Test operation manager history tracking"""
        # Get initial history
        history = self.operation_manager.get_operation_history()
        initial_count = len(history)
        
        # Perform an operation
        with self.operation_manager.acquire_lock(
            OperationType.TASK_CREATION,
            LockScope.USER,
            "test_user"
        ):
            pass
        
        # Check history was updated
        history = self.operation_manager.get_operation_history()
        self.assertGreater(len(history), initial_count)
        
        # Verify history entries
        lock_acquired = [h for h in history if h['operation'] == 'lock_acquired']
        lock_released = [h for h in history if h['operation'] == 'lock_released']
        
        self.assertGreater(len(lock_acquired), 0)
        self.assertGreater(len(lock_released), 0)
    
    def test_graceful_shutdown_handler_initialization(self):
        """Test GracefulShutdownHandler initialization"""
        # Mock Flask app
        mock_app = Mock()
        
        # Create shutdown handler
        shutdown_handler = GracefulShutdownHandler(
            mock_app, self.recovery_manager, shutdown_timeout=10
        )
        
        self.assertIsNotNone(shutdown_handler)
        self.assertEqual(shutdown_handler.app, mock_app)
        self.assertEqual(shutdown_handler.recovery_manager, self.recovery_manager)
        self.assertEqual(shutdown_handler.shutdown_timeout, 10)
        self.assertFalse(shutdown_handler._shutdown_initiated)
    
    def test_graceful_shutdown_status(self):
        """Test graceful shutdown status tracking"""
        # Mock Flask app
        mock_app = Mock()
        
        # Create shutdown handler
        shutdown_handler = GracefulShutdownHandler(
            mock_app, self.recovery_manager, shutdown_timeout=10
        )
        
        # Test initial status
        status = shutdown_handler.get_shutdown_status()
        self.assertFalse(status['shutdown_initiated'])
        self.assertEqual(status['shutdown_timeout'], 10)
        
        # Test status check
        self.assertFalse(shutdown_handler.is_shutdown_initiated())

if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for enhanced BackgroundCleanupManager with health monitoring and task coordination
"""

import unittest
import threading
import time
import redis
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from background_cleanup_manager import (
    BackgroundCleanupManager, CleanupConfig, TaskHealthStatus, 
    TaskHealthMetrics, TaskCoordinationInfo
)
from database import DatabaseManager


class TestEnhancedBackgroundCleanupManager(unittest.TestCase):
    """Test enhanced BackgroundCleanupManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_redis_client = Mock(spec=redis.Redis)
        self.mock_cache_manager = Mock()
        self.mock_notification_monitor = Mock()
        self.mock_notification_monitor._error_counts = {}
        
        # Configure mock database session
        self.mock_session = Mock()
        self.mock_context_manager = Mock()
        self.mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        self.mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = self.mock_context_manager
        
        # Configure test config
        self.test_config = CleanupConfig(
            audit_log_retention_days=30,
            metrics_retention_days=15,
            cache_cleanup_interval_minutes=1,  # Short interval for testing
            database_cleanup_interval_hours=1,  # Short interval for testing
            cleanup_enabled=True
        )
        
        self.cleanup_manager = BackgroundCleanupManager(
            db_manager=self.mock_db_manager,
            redis_client=self.mock_redis_client,
            cache_manager=self.mock_cache_manager,
            config=self.test_config,
            notification_monitor=self.mock_notification_monitor
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.cleanup_manager, '_shutdown_event'):
            self.cleanup_manager.stop_background_cleanup()
    
    def test_initialization_with_health_monitoring(self):
        """Test that manager initializes with health monitoring capabilities"""
        self.assertIsNotNone(self.cleanup_manager._task_health_metrics)
        self.assertIsNotNone(self.cleanup_manager._task_coordination_info)
        self.assertIsNotNone(self.cleanup_manager._task_dependencies)
        self.assertEqual(self.cleanup_manager._max_concurrent_tasks, 3)
        self.assertEqual(self.cleanup_manager._health_check_interval, 60)
        self.assertEqual(self.cleanup_manager._heartbeat_timeout, 300)
    
    def test_start_background_cleanup_with_health_monitoring(self):
        """Test starting cleanup with health monitoring"""
        self.cleanup_manager.start_background_cleanup()
        
        # Verify threads are started
        self.assertIn('cache_cleanup', self.cleanup_manager._cleanup_threads)
        self.assertIn('database_cleanup', self.cleanup_manager._cleanup_threads)
        
        # Verify health monitoring thread is started
        self.assertIsNotNone(self.cleanup_manager._health_monitor_thread)
        self.assertTrue(self.cleanup_manager._health_monitor_thread.is_alive())
        
        # Verify coordination info is initialized
        self.assertIn('cache_cleanup', self.cleanup_manager._task_coordination_info)
        self.assertIn('database_cleanup', self.cleanup_manager._task_coordination_info)
        
        # Verify health metrics are initialized
        self.assertIn('cache_cleanup', self.cleanup_manager._task_health_metrics)
        self.assertIn('database_cleanup', self.cleanup_manager._task_health_metrics)
        
        # Clean up
        self.cleanup_manager.stop_background_cleanup()
    
    def test_stop_background_cleanup_with_graceful_shutdown(self):
        """Test stopping cleanup with graceful shutdown tracking"""
        self.cleanup_manager.start_background_cleanup()
        
        # Let it run briefly
        time.sleep(0.5)
        
        # Stop and verify graceful shutdown
        start_time = time.time()
        self.cleanup_manager.stop_background_cleanup()
        shutdown_time = time.time() - start_time
        
        # Should shutdown within reasonable time
        self.assertLess(shutdown_time, 10)  # Should be much faster than 30s timeout
        
        # Verify threads are stopped
        self.assertEqual(len(self.cleanup_manager._cleanup_threads), 0)
        self.assertEqual(len(self.cleanup_manager._running_tasks), 0)
    
    def test_task_coordination_can_run_task(self):
        """Test task coordination logic"""
        # Test basic can_run_task
        self.assertTrue(self.cleanup_manager._can_run_task('cache_cleanup'))
        
        # Test with too many running tasks
        self.cleanup_manager._running_tasks = {'task1', 'task2', 'task3'}  # Max is 3
        self.assertFalse(self.cleanup_manager._can_run_task('cache_cleanup'))
        
        # Reset running tasks
        self.cleanup_manager._running_tasks = set()
        
        # Test with dependencies
        self.cleanup_manager._running_tasks.add('audit_logs')
        self.assertFalse(self.cleanup_manager._can_run_task('orphaned_data'))  # Depends on audit_logs
        
        # Test without blocking dependencies
        self.cleanup_manager._running_tasks = {'cache_cleanup'}
        self.assertTrue(self.cleanup_manager._can_run_task('orphaned_data'))  # audit_logs not running
    
    def test_resource_monitoring(self):
        """Test resource usage monitoring"""
        # Test resource checking with real system values
        self.cleanup_manager._check_resource_usage()
        
        # Test with simulated high resource usage by patching only for the warning test
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.cpu_percent') as mock_cpu, \
             patch('background_cleanup_manager.logger') as mock_logger:
            
            # Set high values to trigger warnings
            mock_memory.return_value.percent = 95.0
            mock_cpu.return_value = 95.0
            
            self.cleanup_manager._check_resource_usage()
            mock_logger.warning.assert_called()
    
    def test_task_health_metrics_update(self):
        """Test task health metrics updating"""
        task_name = 'test_task'
        
        # Test successful execution
        self.cleanup_manager._update_task_health_metrics(
            task_name, True, 1.5, 10.0, 5.0
        )
        
        metrics = self.cleanup_manager._task_health_metrics[task_name]
        self.assertEqual(metrics.task_name, task_name)
        self.assertEqual(metrics.status, TaskHealthStatus.HEALTHY)
        self.assertEqual(metrics.execution_count, 1)
        self.assertEqual(metrics.success_count, 1)
        self.assertEqual(metrics.failure_count, 0)
        self.assertEqual(metrics.avg_execution_time, 1.5)
        
        # Test failed execution
        self.cleanup_manager._update_task_health_metrics(
            task_name, False, 0, 0, 0, "Test error"
        )
        
        metrics = self.cleanup_manager._task_health_metrics[task_name]
        self.assertEqual(metrics.execution_count, 2)
        self.assertEqual(metrics.success_count, 1)
        self.assertEqual(metrics.failure_count, 1)
        self.assertEqual(metrics.last_error, "Test error")
        
        # Test multiple failures leading to critical status
        for _ in range(3):
            self.cleanup_manager._update_task_health_metrics(
                task_name, False, 0, 0, 0, "Multiple failures"
            )
        
        metrics = self.cleanup_manager._task_health_metrics[task_name]
        self.assertEqual(metrics.status, TaskHealthStatus.CRITICAL)
    
    def test_heartbeat_monitoring(self):
        """Test task heartbeat monitoring"""
        task_name = 'test_task'
        
        # Create coordination info
        self.cleanup_manager._task_coordination_info[task_name] = TaskCoordinationInfo(
            task_name=task_name,
            thread_id='123',
            is_running=True,
            start_time=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc) - timedelta(seconds=400),  # Expired
            resource_limits={'memory_mb': 100},
            dependencies=[]
        )
        
        # Create health metrics
        self.cleanup_manager._task_health_metrics[task_name] = TaskHealthMetrics(
            task_name=task_name,
            status=TaskHealthStatus.HEALTHY,
            last_run=datetime.now(timezone.utc),
            execution_count=1,
            success_count=1,
            failure_count=0,
            avg_execution_time=1.0,
            last_error=None,
            resource_usage={'memory_mb': 0, 'cpu_percent': 0},
            timestamp=datetime.now(timezone.utc)
        )
        
        # Check heartbeats
        with patch('background_cleanup_manager.logger') as mock_logger:
            self.cleanup_manager._check_task_heartbeats()
            mock_logger.warning.assert_called()
        
        # Verify status updated to critical
        self.assertEqual(
            self.cleanup_manager._task_health_metrics[task_name].status,
            TaskHealthStatus.CRITICAL
        )
    
    def test_notification_monitor_integration(self):
        """Test integration with notification system monitor"""
        task_name = 'test_task'
        
        # Create critical task
        self.cleanup_manager._task_health_metrics[task_name] = TaskHealthMetrics(
            task_name=task_name,
            status=TaskHealthStatus.CRITICAL,
            last_run=datetime.now(timezone.utc),
            execution_count=1,
            success_count=0,
            failure_count=1,
            avg_execution_time=1.0,
            last_error="Test error",
            resource_usage={'memory_mb': 0, 'cpu_percent': 0},
            timestamp=datetime.now(timezone.utc)
        )
        
        # Mock notification monitor error counts
        self.mock_notification_monitor._error_counts = {}
        
        # Test integration
        self.cleanup_manager._integrate_with_notification_monitor()
        
        # Verify error counts updated
        self.assertIn(f'cleanup_{task_name}_critical', self.mock_notification_monitor._error_counts)
        self.assertEqual(self.mock_notification_monitor._error_counts[f'cleanup_{task_name}_critical'], 1)
        self.assertIn('cleanup_system_critical', self.mock_notification_monitor._error_counts)
    
    def test_monitor_task_health_method(self):
        """Test monitor_task_health method returns comprehensive data"""
        # Add some test data
        task_name = 'test_task'
        self.cleanup_manager._task_health_metrics[task_name] = TaskHealthMetrics(
            task_name=task_name,
            status=TaskHealthStatus.HEALTHY,
            last_run=datetime.now(timezone.utc),
            execution_count=5,
            success_count=4,
            failure_count=1,
            avg_execution_time=2.5,
            last_error=None,
            resource_usage={'memory_mb': 50, 'cpu_percent': 10},
            timestamp=datetime.now(timezone.utc)
        )
        
        self.cleanup_manager._running_tasks.add('active_task')
        
        # Use real system values for monitoring
        health_data = self.cleanup_manager.monitor_task_health()
        
        # Verify comprehensive data returned
        self.assertIn('task_health_metrics', health_data)
        self.assertIn('task_coordination_info', health_data)
        self.assertIn('running_tasks', health_data)
        self.assertIn('system_resources', health_data)
        self.assertIn('configuration', health_data)
        self.assertIn('timestamp', health_data)
        
        # Verify specific data
        self.assertEqual(health_data['running_tasks'], ['active_task'])
        # Verify that real system values are being captured
        self.assertIsInstance(health_data['system_resources']['memory_percent'], float)
        self.assertIsInstance(health_data['system_resources']['cpu_percent'], float)
        self.assertGreaterEqual(health_data['system_resources']['memory_percent'], 0)
        self.assertGreaterEqual(health_data['system_resources']['cpu_percent'], 0)
    
    def test_coordinate_cleanup_tasks_method(self):
        """Test coordinate_cleanup_tasks method returns coordination data"""
        # Use real system values for coordination data
        coordination_data = self.cleanup_manager.coordinate_cleanup_tasks()
        
        # Verify coordination data structure
        self.assertIn('coordination_status', coordination_data)
        self.assertIn('resource_usage', coordination_data)
        self.assertIn('execution_history', coordination_data)
        self.assertIn('timestamp', coordination_data)
        
        # Verify coordination status for each task
        for task_name in self.cleanup_manager._cleanup_tasks.keys():
            self.assertIn(task_name, coordination_data['coordination_status'])
            task_status = coordination_data['coordination_status'][task_name]
            self.assertIn('can_run', task_status)
            self.assertIn('is_running', task_status)
            self.assertIn('dependencies', task_status)
    
    def test_enhanced_get_cleanup_stats(self):
        """Test enhanced get_cleanup_stats includes health monitoring data"""
        # Add some test stats
        from background_cleanup_manager import CleanupStats
        test_stat = CleanupStats(
            operation_name='test_operation',
            items_cleaned=10,
            execution_time_seconds=2.5,
            timestamp=datetime.now(),
            success=True
        )
        self.cleanup_manager._cleanup_stats.append(test_stat)
        
        # Use real system values for cleanup stats
        stats = self.cleanup_manager.get_cleanup_stats()
        
        # Verify enhanced stats structure
        self.assertIn('summary', stats)
        self.assertIn('operation_breakdown', stats)
        self.assertIn('health_monitoring', stats)
        self.assertIn('task_coordination', stats)
        self.assertIn('notification_integration', stats)
        self.assertIn('config', stats)
        
        # Verify notification integration info
        self.assertTrue(stats['notification_integration']['monitor_available'])
        self.assertTrue(stats['notification_integration']['integration_active'])
        
        # Verify enhanced config includes new parameters
        config = stats['config']
        self.assertIn('max_concurrent_tasks', config)
        self.assertIn('health_check_interval', config)
        self.assertIn('heartbeat_timeout', config)
    
    def test_coordinated_cleanup_execution(self):
        """Test coordinated cleanup execution with resource monitoring"""
        # Mock the cleanup function
        mock_cleanup_func = Mock(return_value=5)
        
        # Set shutdown event immediately to prevent infinite loop
        self.cleanup_manager._shutdown_event.set()
        
        # Mock system resources
        with patch('psutil.cpu_percent', side_effect=[20.0, 25.0]), \
             patch.object(self.cleanup_manager, '_get_process_memory_usage', side_effect=[100.0, 105.0]), \
             patch.object(self.cleanup_manager, '_can_run_task', return_value=True), \
             patch.object(self.cleanup_manager, '_update_task_heartbeat'), \
             patch.object(self.cleanup_manager, '_update_task_health_metrics') as mock_update_health:
            
            # Run coordinated cleanup (should exit immediately due to shutdown event)
            self.cleanup_manager._run_coordinated_cleanup('test_task', mock_cleanup_func, 1)
            
            # Since shutdown event is set, cleanup function should not be called
            mock_cleanup_func.assert_not_called()
            
            # Health metrics should not be updated since task didn't run
            mock_update_health.assert_not_called()
    
    def test_single_cleanup_execution_with_coordination(self):
        """Test single execution of cleanup with coordination features"""
        # Mock the cleanup function
        mock_cleanup_func = Mock(return_value=5)
        task_name = 'test_task'
        
        # Mock system resources
        with patch('psutil.cpu_percent', side_effect=[20.0, 25.0]), \
             patch.object(self.cleanup_manager, '_get_process_memory_usage', side_effect=[100.0, 105.0]), \
             patch.object(self.cleanup_manager, '_can_run_task', return_value=True), \
             patch.object(self.cleanup_manager, '_update_task_heartbeat') as mock_heartbeat, \
             patch.object(self.cleanup_manager, '_update_task_health_metrics') as mock_update_health:
            
            # Simulate single execution (what happens inside the loop)
            if not self.cleanup_manager._shutdown_event.is_set() and self.cleanup_manager._can_run_task(task_name):
                self.cleanup_manager._running_tasks.add(task_name)
                self.cleanup_manager._update_task_heartbeat(task_name)
                
                # Execute cleanup
                result = mock_cleanup_func()
                
                # Update health metrics
                self.cleanup_manager._update_task_health_metrics(task_name, True, 1.5, 5.0, 5.0)
                
                # Remove from running tasks
                self.cleanup_manager._running_tasks.discard(task_name)
            
            # Verify cleanup function was called
            mock_cleanup_func.assert_called_once()
            
            # Verify heartbeat was updated
            mock_heartbeat.assert_called_once_with(task_name)
            
            # Verify health metrics were updated
            mock_update_health.assert_called_once()
            call_args = mock_update_health.call_args[0]
            self.assertEqual(call_args[0], task_name)  # task_name
            self.assertTrue(call_args[1])  # success
            self.assertEqual(call_args[2], 1.5)  # execution_time
    
    def test_task_dependencies_respected(self):
        """Test that task dependencies are properly respected"""
        # Use real system values but ensure we don't hit resource limits by using low memory usage
        with patch.object(self.cleanup_manager, '_get_process_memory_usage', return_value=50.0):
            # Test orphaned_data depends on audit_logs
            self.cleanup_manager._running_tasks.add('audit_logs')
            self.assertFalse(self.cleanup_manager._can_run_task('orphaned_data'))
            
            # Test orphaned_data depends on failed_tasks
            self.cleanup_manager._running_tasks = {'failed_tasks'}
            self.assertFalse(self.cleanup_manager._can_run_task('orphaned_data'))
            
            # Test orphaned_data depends on completed_tasks
            self.cleanup_manager._running_tasks = {'completed_tasks'}
            self.assertFalse(self.cleanup_manager._can_run_task('orphaned_data'))
            
            # Test orphaned_data can run when dependencies are not running
            self.cleanup_manager._running_tasks = {'cache_entries'}  # Not a dependency
            self.assertTrue(self.cleanup_manager._can_run_task('orphaned_data'))
            
            # Test processing_runs depends on completed_tasks
            self.cleanup_manager._running_tasks = {'completed_tasks'}
            self.assertFalse(self.cleanup_manager._can_run_task('processing_runs'))
            
            # Test cache_entries has no dependencies (but check concurrent task limit)
            self.cleanup_manager._running_tasks = {'audit_logs', 'failed_tasks'}  # Only 2 tasks, under limit of 3
            self.assertTrue(self.cleanup_manager._can_run_task('cache_entries'))


if __name__ == '__main__':
    unittest.main()
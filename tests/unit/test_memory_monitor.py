# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Memory Monitor

Tests memory monitoring and enforcement during job execution with
graceful termination when memory limits are exceeded.
"""

import unittest
import os
import sys
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from memory_monitor import (
    MemoryMonitor,
    MemoryMonitorStatus,
    MemoryMonitorConfig
)
from performance_configuration_adapter import MemoryUsageInfo


class TestMemoryMonitorConfig(unittest.TestCase):
    """Test MemoryMonitorConfig"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = MemoryMonitorConfig()
        
        self.assertEqual(config.check_interval_seconds, 5.0)
        self.assertEqual(config.warning_threshold_percent, 80.0)
        self.assertEqual(config.critical_threshold_percent, 95.0)
        self.assertEqual(config.grace_period_seconds, 10.0)
        self.assertTrue(config.enable_graceful_termination)
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = MemoryMonitorConfig(
            check_interval_seconds=1.0,
            warning_threshold_percent=70.0,
            critical_threshold_percent=90.0,
            grace_period_seconds=5.0,
            enable_graceful_termination=False
        )
        
        self.assertEqual(config.check_interval_seconds, 1.0)
        self.assertEqual(config.warning_threshold_percent, 70.0)
        self.assertEqual(config.critical_threshold_percent, 90.0)
        self.assertEqual(config.grace_period_seconds, 5.0)
        self.assertFalse(config.enable_graceful_termination)


class TestMemoryMonitor(unittest.TestCase):
    """Test MemoryMonitor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_performance_adapter = Mock()
        
        # Create test configuration with short intervals for faster testing
        self.test_config = MemoryMonitorConfig(
            check_interval_seconds=0.1,  # Very short for testing
            warning_threshold_percent=80.0,
            critical_threshold_percent=95.0,
            grace_period_seconds=1.0,
            enable_graceful_termination=True
        )
        
        self.monitor = MemoryMonitor(self.mock_performance_adapter, self.test_config)
    
    def test_initialization(self):
        """Test monitor initialization"""
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.STOPPED)
        self.assertIsNone(self.monitor._process_id)
        self.assertIsNone(self.monitor._task_id)
        self.assertEqual(self.monitor._warning_count, 0)
        self.assertEqual(self.monitor._limit_exceeded_count, 0)
    
    @patch('psutil.Process')
    def test_start_monitoring_success(self, mock_process_class):
        """Test successful monitoring start"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        result = self.monitor.start_monitoring(process_id=123, task_id="test-task")
        
        self.assertTrue(result)
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.RUNNING)
        self.assertEqual(self.monitor._process_id, 123)
        self.assertEqual(self.monitor._task_id, "test-task")
        self.assertTrue(self.monitor.is_monitoring())
        
        # Clean up
        self.monitor.stop_monitoring()
    
    @patch('psutil.Process')
    def test_start_monitoring_process_not_found(self, mock_process_class):
        """Test monitoring start with non-existent process"""
        import psutil
        mock_process_class.side_effect = psutil.NoSuchProcess(123)
        
        result = self.monitor.start_monitoring(process_id=123)
        
        self.assertFalse(result)
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.STOPPED)
    
    @patch('psutil.Process')
    def test_start_monitoring_already_running(self, mock_process_class):
        """Test starting monitoring when already running"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        # Start monitoring
        self.monitor.start_monitoring(process_id=123)
        
        # Try to start again
        result = self.monitor.start_monitoring(process_id=456)
        
        self.assertFalse(result)
        self.assertEqual(self.monitor._process_id, 123)  # Should keep original process
        
        # Clean up
        self.monitor.stop_monitoring()
    
    @patch('psutil.Process')
    def test_stop_monitoring(self, mock_process_class):
        """Test stopping monitoring"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        # Start monitoring
        self.monitor.start_monitoring(process_id=123)
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.RUNNING)
        
        # Stop monitoring
        result = self.monitor.stop_monitoring()
        
        self.assertTrue(result)
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.STOPPED)
        self.assertFalse(self.monitor.is_monitoring())
    
    def test_stop_monitoring_not_running(self):
        """Test stopping monitoring when not running"""
        result = self.monitor.stop_monitoring()
        
        self.assertTrue(result)
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.STOPPED)
    
    def test_callback_setters(self):
        """Test setting callbacks"""
        warning_callback = Mock()
        limit_exceeded_callback = Mock()
        termination_callback = Mock()
        
        self.monitor.set_warning_callback(warning_callback)
        self.monitor.set_limit_exceeded_callback(limit_exceeded_callback)
        self.monitor.set_termination_callback(termination_callback)
        
        self.assertEqual(self.monitor._warning_callback, warning_callback)
        self.assertEqual(self.monitor._limit_exceeded_callback, limit_exceeded_callback)
        self.assertEqual(self.monitor._termination_callback, termination_callback)
    
    @patch('psutil.Process')
    def test_memory_usage_monitoring_normal(self, mock_process_class):
        """Test memory usage monitoring within normal limits"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        # Mock memory usage within limits (50% of 1024MB limit)
        usage_info = MemoryUsageInfo(
            current_mb=512.0,
            limit_mb=1024,
            percentage=50.0,
            process_id=123,
            timestamp=datetime.now(timezone.utc)
        )
        self.mock_performance_adapter.check_memory_usage.return_value = usage_info
        
        # Start monitoring
        self.monitor.start_monitoring(process_id=123)
        
        # Let it run for a short time
        time.sleep(0.2)
        
        # Should still be running normally
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.RUNNING)
        self.assertEqual(self.monitor._warning_count, 0)
        
        # Clean up
        self.monitor.stop_monitoring()
    
    @patch('psutil.Process')
    def test_memory_usage_monitoring_warning(self, mock_process_class):
        """Test memory usage monitoring with warning threshold exceeded"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        # Mock memory usage at warning threshold (85% of 1024MB limit)
        usage_info = MemoryUsageInfo(
            current_mb=870.4,
            limit_mb=1024,
            percentage=85.0,
            process_id=123,
            timestamp=datetime.now(timezone.utc)
        )
        self.mock_performance_adapter.check_memory_usage.return_value = usage_info
        
        # Set up warning callback
        warning_callback = Mock()
        self.monitor.set_warning_callback(warning_callback)
        
        # Start monitoring
        self.monitor.start_monitoring(process_id=123)
        
        # Let it run for a short time
        time.sleep(0.2)
        
        # Should be in warning state
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.WARNING)
        self.assertGreater(self.monitor._warning_count, 0)
        
        # Warning callback should have been called
        warning_callback.assert_called()
        
        # Clean up
        self.monitor.stop_monitoring()
    
    @patch('psutil.Process')
    def test_memory_usage_monitoring_limit_exceeded(self, mock_process_class):
        """Test memory usage monitoring with limit exceeded"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        # Mock memory usage exceeding limit (110% of 1024MB limit)
        usage_info = MemoryUsageInfo(
            current_mb=1126.4,
            limit_mb=1024,
            percentage=110.0,
            process_id=123,
            timestamp=datetime.now(timezone.utc)
        )
        self.mock_performance_adapter.check_memory_usage.return_value = usage_info
        
        # Set up callbacks
        limit_exceeded_callback = Mock()
        termination_callback = Mock()
        self.monitor.set_limit_exceeded_callback(limit_exceeded_callback)
        self.monitor.set_termination_callback(termination_callback)
        
        # Disable graceful termination for this test
        self.monitor.config.enable_graceful_termination = False
        
        # Start monitoring
        self.monitor.start_monitoring(process_id=123)
        
        # Let it run for a short time
        time.sleep(0.2)
        
        # Should be in limit exceeded state
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.LIMIT_EXCEEDED)
        self.assertGreater(self.monitor._limit_exceeded_count, 0)
        
        # Limit exceeded callback should have been called
        limit_exceeded_callback.assert_called()
        
        # Clean up
        self.monitor.stop_monitoring()
    
    @patch('psutil.Process')
    def test_process_termination_graceful(self, mock_process_class):
        """Test graceful process termination"""
        # Mock target process (not current process)
        mock_process = Mock()
        mock_process.pid = 456  # Different from current process
        mock_process_class.return_value = mock_process
        
        # Mock memory usage exceeding limit
        usage_info = MemoryUsageInfo(
            current_mb=1126.4,
            limit_mb=1024,
            percentage=110.0,
            process_id=456,
            timestamp=datetime.now(timezone.utc)
        )
        self.mock_performance_adapter.check_memory_usage.return_value = usage_info
        
        # Set up termination callback
        termination_callback = Mock()
        self.monitor.set_termination_callback(termination_callback)
        
        # Start monitoring
        self.monitor.start_monitoring(process_id=456)
        
        # Let it run for a short time
        time.sleep(0.2)
        
        # Process should have been terminated
        mock_process.terminate.assert_called()
        termination_callback.assert_called()
        
        # Clean up
        self.monitor.stop_monitoring()
    
    @patch('psutil.Process')
    def test_process_not_found_during_monitoring(self, mock_process_class):
        """Test handling of process disappearing during monitoring"""
        import psutil
        
        # Mock process exists initially
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        # Start monitoring
        self.monitor.start_monitoring(process_id=123)
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.RUNNING)
        
        # Mock process disappearing
        self.mock_performance_adapter.check_memory_usage.side_effect = psutil.NoSuchProcess(123)
        
        # Let it run for a short time
        time.sleep(0.2)
        
        # Should have stopped monitoring
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.STOPPED)
    
    @patch('psutil.Process')
    def test_get_statistics(self, mock_process_class):
        """Test getting monitoring statistics"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        # Mock current memory usage
        usage_info = MemoryUsageInfo(
            current_mb=512.0,
            limit_mb=1024,
            percentage=50.0,
            process_id=123,
            timestamp=datetime.now(timezone.utc)
        )
        self.mock_performance_adapter.check_memory_usage.return_value = usage_info
        
        # Start monitoring
        self.monitor.start_monitoring(process_id=123, task_id="test-task")
        
        # Get statistics
        stats = self.monitor.get_statistics()
        
        self.assertEqual(stats['status'], MemoryMonitorStatus.RUNNING.value)
        self.assertEqual(stats['process_id'], 123)
        self.assertEqual(stats['task_id'], "test-task")
        self.assertIn('current_memory', stats)
        self.assertIn('config', stats)
        self.assertIn('start_time', stats)
        
        # Clean up
        self.monitor.stop_monitoring()
    
    def test_get_statistics_stopped(self):
        """Test getting statistics when monitor is stopped"""
        stats = self.monitor.get_statistics()
        
        self.assertEqual(stats['status'], MemoryMonitorStatus.STOPPED.value)
        self.assertIsNone(stats['process_id'])
        self.assertIsNone(stats['task_id'])
        self.assertEqual(stats['warning_count'], 0)
        self.assertEqual(stats['limit_exceeded_count'], 0)
    
    @patch('psutil.Process')
    def test_context_manager(self, mock_process_class):
        """Test using monitor as context manager"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        with self.monitor as monitor:
            result = monitor.start_monitoring(process_id=123)
            self.assertTrue(result)
            self.assertEqual(monitor.get_status(), MemoryMonitorStatus.RUNNING)
        
        # Should have stopped monitoring when exiting context
        self.assertEqual(self.monitor.get_status(), MemoryMonitorStatus.STOPPED)
    
    @patch('psutil.Process')
    def test_max_memory_usage_tracking(self, mock_process_class):
        """Test tracking of maximum memory usage"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        # Mock increasing memory usage
        usage_values = [
            MemoryUsageInfo(512.0, 1024, 50.0, 123, datetime.now(timezone.utc)),
            MemoryUsageInfo(768.0, 1024, 75.0, 123, datetime.now(timezone.utc)),
            MemoryUsageInfo(640.0, 1024, 62.5, 123, datetime.now(timezone.utc))  # Decrease
        ]
        
        self.mock_performance_adapter.check_memory_usage.side_effect = usage_values
        
        # Start monitoring
        self.monitor.start_monitoring(process_id=123)
        
        # Let it run through multiple checks
        time.sleep(0.3)
        
        # Should track maximum usage (768.0)
        stats = self.monitor.get_statistics()
        self.assertEqual(stats['max_memory_usage_mb'], 768.0)
        
        # Clean up
        self.monitor.stop_monitoring()


class TestMemoryMonitorIntegration(unittest.TestCase):
    """Integration tests for memory monitor"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_performance_adapter = Mock()
        
        # Fast configuration for testing
        self.test_config = MemoryMonitorConfig(
            check_interval_seconds=0.05,
            warning_threshold_percent=70.0,
            critical_threshold_percent=90.0,
            grace_period_seconds=0.5,
            enable_graceful_termination=False  # Disable for safety in tests
        )
    
    @patch('psutil.Process')
    def test_full_monitoring_cycle(self, mock_process_class):
        """Test complete monitoring cycle from normal to limit exceeded"""
        # Mock process exists
        mock_process = Mock()
        mock_process_class.return_value = mock_process
        
        monitor = MemoryMonitor(self.mock_performance_adapter, self.test_config)
        
        # Set up callbacks to track state changes
        warning_calls = []
        limit_exceeded_calls = []
        
        def warning_callback(current_mb, limit_mb):
            warning_calls.append((current_mb, limit_mb))
        
        def limit_exceeded_callback(error_msg):
            limit_exceeded_calls.append(error_msg)
        
        monitor.set_warning_callback(warning_callback)
        monitor.set_limit_exceeded_callback(limit_exceeded_callback)
        
        # Simulate memory usage progression
        usage_progression = [
            # Normal usage
            MemoryUsageInfo(500.0, 1024, 48.8, 123, datetime.now(timezone.utc)),
            # Warning threshold (70%)
            MemoryUsageInfo(716.8, 1024, 70.0, 123, datetime.now(timezone.utc)),
            # Critical threshold (90%)
            MemoryUsageInfo(921.6, 1024, 90.0, 123, datetime.now(timezone.utc)),
            # Limit exceeded
            MemoryUsageInfo(1100.0, 1024, 107.4, 123, datetime.now(timezone.utc))
        ]
        
        self.mock_performance_adapter.check_memory_usage.side_effect = usage_progression
        
        # Start monitoring
        monitor.start_monitoring(process_id=123, task_id="integration-test")
        
        # Let it run through the progression
        time.sleep(0.3)
        
        # Verify state progression
        self.assertEqual(monitor.get_status(), MemoryMonitorStatus.LIMIT_EXCEEDED)
        self.assertGreater(len(warning_calls), 0)
        self.assertGreater(len(limit_exceeded_calls), 0)
        
        # Verify statistics
        stats = monitor.get_statistics()
        self.assertGreater(stats['warning_count'], 0)
        self.assertGreater(stats['limit_exceeded_count'], 0)
        self.assertEqual(stats['max_memory_usage_mb'], 1100.0)
        
        # Clean up
        monitor.stop_monitoring()


if __name__ == '__main__':
    unittest.main()
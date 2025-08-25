# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for queue size limiting functionality

Tests queue size enforcement, monitoring, and alerting capabilities.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
import time
import threading
from datetime import datetime, timezone, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from queue_size_monitor import QueueSizeMonitor, AlertLevel, QueueAlert
from task_queue_manager import TaskQueueManager
from task_queue_configuration_adapter import TaskQueueConfigurationAdapter


class TestQueueSizeLimiting(unittest.TestCase):
    """Test cases for queue size limiting functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock TaskQueueManager
        self.mock_task_queue_manager = Mock()
        self.mock_task_queue_manager.queue_size_limit = 100
        self.mock_task_queue_manager.get_queue_stats.return_value = {
            'queued': 50,
            'running': 2,
            'completed': 10,
            'failed': 1,
            'total': 63
        }
        
        # Mock ConfigurationService
        self.mock_config_service = Mock()
        self.config_values = {
            'queue_monitor_warning_threshold': 0.8,
            'queue_monitor_critical_threshold': 0.95,
            'queue_monitor_check_interval': 30,
            'queue_monitor_alert_suppression_time': 300
        }
        self.mock_config_service.get_config.side_effect = self._mock_get_config
        
        # Alert callback mock
        self.alert_callback = Mock()
        
        # Create monitor
        self.monitor = QueueSizeMonitor(
            task_queue_manager=self.mock_task_queue_manager,
            config_service=self.mock_config_service,
            alert_callback=self.alert_callback
        )
    
    def _mock_get_config(self, key, default=None):
        """Mock configuration service get_config method"""
        return self.config_values.get(key, default)
    
    def test_monitor_initialization(self):
        """Test queue size monitor initialization"""
        # Verify configuration was loaded
        self.assertEqual(self.monitor.warning_threshold, 0.8)
        self.assertEqual(self.monitor.critical_threshold, 0.95)
        self.assertEqual(self.monitor.check_interval, 30)
        self.assertEqual(self.monitor.alert_suppression_time, 300)
        
        # Verify initial state
        self.assertFalse(self.monitor.is_monitoring())
        self.assertEqual(len(self.monitor._alert_history), 0)
    
    def test_monitor_initialization_without_config_service(self):
        """Test monitor initialization without configuration service"""
        monitor = QueueSizeMonitor(
            task_queue_manager=self.mock_task_queue_manager
        )
        
        # Verify default values
        self.assertEqual(monitor.warning_threshold, 0.8)
        self.assertEqual(monitor.critical_threshold, 0.95)
        self.assertEqual(monitor.check_interval, 30)
        self.assertEqual(monitor.alert_suppression_time, 300)
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        # Start monitoring
        result = self.monitor.start_monitoring()
        self.assertTrue(result)
        self.assertTrue(self.monitor.is_monitoring())
        
        # Try to start again (should fail)
        result = self.monitor.start_monitoring()
        self.assertFalse(result)
        
        # Stop monitoring
        result = self.monitor.stop_monitoring()
        self.assertTrue(result)
        self.assertFalse(self.monitor.is_monitoring())
        
        # Try to stop again (should fail)
        result = self.monitor.stop_monitoring()
        self.assertFalse(result)
    
    def test_queue_size_check_normal(self):
        """Test queue size check under normal conditions"""
        # Set queue size to 50% of limit
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 50}
        
        # Check queue size
        self.monitor._check_queue_size()
        
        # Should not generate any alerts
        self.assertEqual(len(self.monitor._alert_history), 0)
        self.alert_callback.assert_not_called()
    
    def test_queue_size_check_warning_threshold(self):
        """Test queue size check at warning threshold"""
        # Set queue size to 85% of limit (above 80% warning threshold)
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 85}
        
        # Check queue size
        self.monitor._check_queue_size()
        
        # Should generate warning alert
        self.assertEqual(len(self.monitor._alert_history), 1)
        alert = self.monitor._alert_history[0]
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertEqual(alert.current_size, 85)
        self.assertEqual(alert.limit, 100)
        self.alert_callback.assert_called_once_with(alert)
    
    def test_queue_size_check_critical_threshold(self):
        """Test queue size check at critical threshold"""
        # Set queue size to 98% of limit (above 95% critical threshold)
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 98}
        
        # Check queue size
        self.monitor._check_queue_size()
        
        # Should generate critical alert
        self.assertEqual(len(self.monitor._alert_history), 1)
        alert = self.monitor._alert_history[0]
        self.assertEqual(alert.level, AlertLevel.CRITICAL)
        self.assertEqual(alert.current_size, 98)
        self.assertEqual(alert.limit, 100)
        self.alert_callback.assert_called_once_with(alert)
    
    def test_queue_size_check_queue_cleared(self):
        """Test queue size check when queue is cleared after alerts"""
        # First generate a warning alert
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 85}
        self.monitor._check_queue_size()
        self.assertEqual(len(self.monitor._alert_history), 1)
        
        # Then clear the queue
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 0}
        self.monitor._check_queue_size()
        
        # Should generate info alert about normalization
        self.assertEqual(len(self.monitor._alert_history), 2)
        alert = self.monitor._alert_history[1]
        self.assertEqual(alert.level, AlertLevel.INFO)
        self.assertEqual(alert.current_size, 0)
        self.assertIn("normalized", alert.message)
    
    def test_alert_suppression(self):
        """Test alert suppression to prevent spam"""
        # Set short suppression time for testing
        self.monitor.alert_suppression_time = 1
        
        # Generate first alert
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 85}
        self.monitor._check_queue_size()
        self.assertEqual(len(self.monitor._alert_history), 1)
        
        # Generate same alert immediately (should be suppressed)
        self.monitor._check_queue_size()
        self.assertEqual(len(self.monitor._alert_history), 1)
        
        # Wait for suppression to expire
        time.sleep(1.1)
        
        # Generate same alert again (should not be suppressed)
        self.monitor._check_queue_size()
        self.assertEqual(len(self.monitor._alert_history), 2)
    
    def test_get_current_status(self):
        """Test getting current monitoring status"""
        status = self.monitor.get_current_status()
        
        expected_keys = [
            'monitoring_active', 'current_queue_size', 'queue_size_limit',
            'utilization_percentage', 'warning_threshold', 'critical_threshold',
            'check_interval', 'recent_alerts', 'last_check'
        ]
        
        for key in expected_keys:
            self.assertIn(key, status)
        
        self.assertEqual(status['current_queue_size'], 50)
        self.assertEqual(status['queue_size_limit'], 100)
        self.assertEqual(status['utilization_percentage'], 0.5)
        self.assertFalse(status['monitoring_active'])
    
    def test_get_statistics(self):
        """Test getting monitoring statistics"""
        # Update statistics
        self.monitor._update_statistics()
        
        stats = self.monitor.get_statistics()
        
        expected_keys = [
            'max_size_observed', 'min_size_observed', 'total_checks',
            'alert_counts', 'last_updated', 'average_size', 'size_history'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
        
        self.assertEqual(stats['total_checks'], 1)
        self.assertEqual(stats['max_size_observed'], 50)
        self.assertEqual(stats['min_size_observed'], 50)
    
    def test_get_alert_history(self):
        """Test getting alert history"""
        # Generate some alerts
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 85}
        self.monitor._check_queue_size()
        
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 98}
        self.monitor._check_queue_size()
        
        # Get alert history
        alerts = self.monitor.get_alert_history(hours=24)
        self.assertEqual(len(alerts), 2)
        
        # Check alert types
        self.assertEqual(alerts[0].level, AlertLevel.WARNING)
        self.assertEqual(alerts[1].level, AlertLevel.CRITICAL)
    
    def test_update_thresholds_success(self):
        """Test successful threshold updates"""
        result = self.monitor.update_thresholds(
            warning_threshold=0.7,
            critical_threshold=0.9
        )
        
        self.assertTrue(result)
        self.assertEqual(self.monitor.warning_threshold, 0.7)
        self.assertEqual(self.monitor.critical_threshold, 0.9)
    
    def test_update_thresholds_invalid_values(self):
        """Test threshold updates with invalid values"""
        # Test invalid warning threshold
        result = self.monitor.update_thresholds(warning_threshold=1.5)
        self.assertFalse(result)
        
        # Test invalid critical threshold
        result = self.monitor.update_thresholds(critical_threshold=-0.1)
        self.assertFalse(result)
        
        # Test warning >= critical
        result = self.monitor.update_thresholds(
            warning_threshold=0.9,
            critical_threshold=0.8
        )
        self.assertFalse(result)
    
    def test_force_check(self):
        """Test forced queue size check"""
        self.mock_task_queue_manager.get_queue_stats.return_value = {'queued': 85}
        
        result = self.monitor.force_check()
        
        # Should generate alert and return status
        self.assertEqual(len(self.monitor._alert_history), 1)
        self.assertIn('current_queue_size', result)
        self.assertEqual(result['current_queue_size'], 85)
    
    def test_monitor_with_no_limit(self):
        """Test monitoring when no queue limit is configured"""
        # Set queue limit to 0 (no limit)
        self.mock_task_queue_manager.queue_size_limit = 0
        
        # Check queue size
        self.monitor._check_queue_size()
        
        # Should not generate any alerts
        self.assertEqual(len(self.monitor._alert_history), 0)
    
    def test_monitor_error_handling(self):
        """Test error handling in monitoring"""
        # Make get_queue_stats raise an exception
        self.mock_task_queue_manager.get_queue_stats.side_effect = Exception("Database error")
        
        # Should not crash
        self.monitor._check_queue_size()
        self.monitor._update_statistics()
        
        # Should return error in status
        status = self.monitor.get_current_status()
        self.assertIn('error', status)
    
    def test_cleanup(self):
        """Test monitor cleanup"""
        # Start monitoring
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor.is_monitoring())
        
        # Cleanup
        self.monitor.cleanup()
        self.assertFalse(self.monitor.is_monitoring())


class TestTaskQueueManagerQueueLimiting(unittest.TestCase):
    """Test queue size limiting in TaskQueueManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock DatabaseManager
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Create TaskQueueManager with queue size limit
        self.task_queue_manager = TaskQueueManager(
            db_manager=self.mock_db_manager,
            max_concurrent_tasks=3
        )
        self.task_queue_manager.queue_size_limit = 10
    
    def test_enqueue_task_within_limit(self):
        """Test task enqueue when within queue size limit"""
        # Mock task
        mock_task = Mock()
        mock_task.id = None
        mock_task.user_id = 123
        mock_task.priority = None
        
        # Mock database queries
        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = None
        self.mock_session.query.return_value.filter_by.return_value.count.return_value = 5  # Under limit
        
        # Mock security manager
        with patch('security.features.caption_security.CaptionSecurityManager') as mock_security_class:
            mock_security = Mock()
            mock_security.generate_secure_task_id.return_value = "task-123"
            mock_security_class.return_value = mock_security
            
            # Should succeed
            result = self.task_queue_manager.enqueue_task(mock_task)
            
            self.assertEqual(result, "task-123")
            self.mock_session.add.assert_called_once_with(mock_task)
            self.mock_session.commit.assert_called_once()
    
    def test_enqueue_task_at_limit(self):
        """Test task enqueue when at queue size limit"""
        # Mock task
        mock_task = Mock()
        mock_task.id = None
        mock_task.user_id = 123
        mock_task.priority = None
        
        # Mock database queries
        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = None
        self.mock_session.query.return_value.filter_by.return_value.count.return_value = 10  # At limit
        
        # Mock security manager
        with patch('security.features.caption_security.CaptionSecurityManager') as mock_security_class:
            mock_security = Mock()
            mock_security.generate_secure_task_id.return_value = "task-123"
            mock_security_class.return_value = mock_security
            
            # Should raise ValueError
            with self.assertRaises(ValueError) as context:
                self.task_queue_manager.enqueue_task(mock_task)
            
            self.assertIn("Queue size limit reached", str(context.exception))
            self.assertIn("10/10", str(context.exception))
            self.mock_session.add.assert_not_called()
    
    def test_enqueue_task_over_limit(self):
        """Test task enqueue when over queue size limit"""
        # Mock task
        mock_task = Mock()
        mock_task.id = None
        mock_task.user_id = 123
        mock_task.priority = None
        
        # Mock database queries
        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = None
        self.mock_session.query.return_value.filter_by.return_value.count.return_value = 15  # Over limit
        
        # Mock security manager
        with patch('security.features.caption_security.CaptionSecurityManager') as mock_security_class:
            mock_security = Mock()
            mock_security.generate_secure_task_id.return_value = "task-123"
            mock_security_class.return_value = mock_security
            
            # Should raise ValueError
            with self.assertRaises(ValueError) as context:
                self.task_queue_manager.enqueue_task(mock_task)
            
            self.assertIn("Queue size limit reached", str(context.exception))
            self.assertIn("15/10", str(context.exception))
            self.mock_session.add.assert_not_called()
    
    def test_enqueue_task_no_limit_configured(self):
        """Test task enqueue when no queue size limit is configured"""
        # Remove queue size limit
        delattr(self.task_queue_manager, 'queue_size_limit')
        
        # Mock task
        mock_task = Mock()
        mock_task.id = None
        mock_task.user_id = 123
        mock_task.priority = None
        
        # Mock database queries
        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = None
        # Don't mock count query since it shouldn't be called
        
        # Mock security manager
        with patch('security.features.caption_security.CaptionSecurityManager') as mock_security_class:
            mock_security = Mock()
            mock_security.generate_secure_task_id.return_value = "task-123"
            mock_security_class.return_value = mock_security
            
            # Should succeed without checking queue size
            result = self.task_queue_manager.enqueue_task(mock_task)
            
            self.assertEqual(result, "task-123")
            self.mock_session.add.assert_called_once_with(mock_task)
            self.mock_session.commit.assert_called_once()
    
    def test_queue_limit_change_during_runtime(self):
        """Test graceful handling of queue limit changes during runtime"""
        # Start with limit of 10
        self.assertEqual(self.task_queue_manager.queue_size_limit, 10)
        
        # Change limit to 5
        result = self.task_queue_manager.update_queue_size_limit(5)
        self.assertTrue(result)
        self.assertEqual(self.task_queue_manager.queue_size_limit, 5)
        
        # Mock task enqueue with current queue size of 7 (over new limit)
        mock_task = Mock()
        mock_task.id = None
        mock_task.user_id = 123
        mock_task.priority = None
        
        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = None
        self.mock_session.query.return_value.filter_by.return_value.count.return_value = 7  # Over new limit
        
        with patch('security.features.caption_security.CaptionSecurityManager') as mock_security_class:
            mock_security = Mock()
            mock_security.generate_secure_task_id.return_value = "task-123"
            mock_security_class.return_value = mock_security
            
            # Should be rejected due to new limit
            with self.assertRaises(ValueError) as context:
                self.task_queue_manager.enqueue_task(mock_task)
            
            self.assertIn("Queue size limit reached", str(context.exception))
            self.assertIn("7/5", str(context.exception))


class TestTaskQueueConfigurationAdapterQueueLimiting(unittest.TestCase):
    """Test queue size limiting in TaskQueueConfigurationAdapter"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock TaskQueueManager
        self.mock_task_queue_manager = Mock()
        self.mock_task_queue_manager.queue_size_limit = 100
        self.mock_task_queue_manager.get_queue_stats.return_value = {
            'queued': 50,
            'running': 2,
            'total': 52
        }
        
        # Mock ConfigurationService
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.return_value = 100
        self.mock_config_service.subscribe_to_changes.return_value = "subscription-123"
        
        # Create adapter
        self.adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
    
    def test_validate_queue_size_allowed(self):
        """Test queue size validation when enqueue is allowed"""
        result = self.adapter.validate_queue_size_before_enqueue(user_id=123)
        self.assertTrue(result)
    
    def test_validate_queue_size_rejected(self):
        """Test queue size validation when enqueue should be rejected"""
        # Set queue stats to show queue is at limit
        self.mock_task_queue_manager.get_queue_stats.return_value = {
            'queued': 100,  # At limit
            'running': 2,
            'total': 102
        }
        
        result = self.adapter.validate_queue_size_before_enqueue(user_id=123)
        self.assertFalse(result)
    
    def test_validate_queue_size_error_handling(self):
        """Test queue size validation with error handling"""
        # Make get_queue_stats raise an exception
        self.mock_task_queue_manager.get_queue_stats.side_effect = Exception("Database error")
        
        # Should fail open (return True) on error
        result = self.adapter.validate_queue_size_before_enqueue(user_id=123)
        self.assertTrue(result)
    
    def test_handle_queue_limit_change_success(self):
        """Test successful queue limit change handling"""
        result = self.adapter.handle_queue_limit_change(150)
        
        self.assertTrue(result)
        self.assertEqual(self.mock_task_queue_manager.queue_size_limit, 150)
    
    def test_handle_queue_limit_change_invalid(self):
        """Test queue limit change with invalid value"""
        original_limit = self.mock_task_queue_manager.queue_size_limit
        
        result = self.adapter.handle_queue_limit_change(-10)
        
        self.assertFalse(result)
        self.assertEqual(self.mock_task_queue_manager.queue_size_limit, original_limit)


if __name__ == '__main__':
    unittest.main()
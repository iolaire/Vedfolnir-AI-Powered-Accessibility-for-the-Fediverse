# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for TaskQueueConfigurationAdapter

Tests the adapter functionality for connecting TaskQueueManager with ConfigurationService
to enable dynamic configuration updates.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.task.configuration.task_queue_configuration_adapter import TaskQueueConfigurationAdapter, TaskQueueConfigurationError
from app.core.configuration.core.configuration_service import ConfigurationError


class TestTaskQueueConfigurationAdapter(unittest.TestCase):
    """Test cases for TaskQueueConfigurationAdapter"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock TaskQueueManager
        self.mock_task_queue_manager = Mock()
        self.mock_task_queue_manager.max_concurrent_tasks = 3
        self.mock_task_queue_manager.default_job_timeout = 3600
        self.mock_task_queue_manager.queue_size_limit = 100
        self.mock_task_queue_manager.get_queue_stats.return_value = {
            'queued': 5,
            'running': 2,
            'completed': 10,
            'failed': 1,
            'cancelled': 0,
            'total': 18,
            'active': 7
        }
        
        # Mock ConfigurationService
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.side_effect = self._mock_get_config
        self.mock_config_service.subscribe_to_changes.return_value = "subscription-id-123"
        
        # Configuration values
        self.config_values = {
            'max_concurrent_jobs': 5,
            'default_job_timeout': 7200,
            'queue_size_limit': 200
        }
    
    def _mock_get_config(self, key, default=None):
        """Mock configuration service get_config method"""
        return self.config_values.get(key, default)
    
    def test_initialization_success(self):
        """Test successful adapter initialization"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Verify configuration was read
        expected_calls = [
            call('max_concurrent_jobs', default=3),
            call('default_job_timeout', default=3600),
            call('queue_size_limit', default=100)
        ]
        self.mock_config_service.get_config.assert_has_calls(expected_calls, any_order=True)
        
        # Verify task queue manager was updated
        self.assertEqual(self.mock_task_queue_manager.max_concurrent_tasks, 5)
        self.assertEqual(self.mock_task_queue_manager.default_job_timeout, 7200)
        self.assertEqual(self.mock_task_queue_manager.queue_size_limit, 200)
        
        # Verify subscriptions were set up
        expected_subscription_calls = [
            call('max_concurrent_jobs', adapter._handle_max_concurrent_jobs_change),
            call('default_job_timeout', adapter._handle_default_job_timeout_change),
            call('queue_size_limit', adapter._handle_queue_size_limit_change)
        ]
        self.mock_config_service.subscribe_to_changes.assert_has_calls(
            expected_subscription_calls, any_order=True
        )
    
    def test_initialization_with_configuration_error(self):
        """Test initialization with configuration service error"""
        self.mock_config_service.get_config.side_effect = ConfigurationError("Config service unavailable")
        
        # Adapter should initialize successfully but log errors
        # It's designed to be resilient and continue working with defaults
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Verify adapter was created
        self.assertIsNotNone(adapter)
        
        # Verify subscriptions were still set up despite config errors
        self.assertEqual(len(adapter._subscriptions), 3)
    
    def test_update_concurrency_limits_success(self):
        """Test successful concurrency limits update"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Update configuration value
        self.config_values['max_concurrent_jobs'] = 10
        
        # Call update method
        result = adapter.update_concurrency_limits()
        
        # Verify success
        self.assertTrue(result)
        self.assertEqual(self.mock_task_queue_manager.max_concurrent_tasks, 10)
    
    def test_update_concurrency_limits_invalid_value(self):
        """Test concurrency limits update with invalid value"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Set invalid configuration value
        self.config_values['max_concurrent_jobs'] = -1
        
        # Call update method
        result = adapter.update_concurrency_limits()
        
        # Verify failure
        self.assertFalse(result)
        # Original value should be preserved
        self.assertEqual(self.mock_task_queue_manager.max_concurrent_tasks, 5)
    
    def test_update_concurrency_limits_non_integer(self):
        """Test concurrency limits update with non-integer value"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Set non-integer configuration value
        self.config_values['max_concurrent_jobs'] = "invalid"
        
        # Call update method
        result = adapter.update_concurrency_limits()
        
        # Verify failure
        self.assertFalse(result)
    
    def test_update_timeout_settings_success(self):
        """Test successful timeout settings update"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Update configuration value
        self.config_values['default_job_timeout'] = 1800
        
        # Call update method
        result = adapter.update_timeout_settings()
        
        # Verify success
        self.assertTrue(result)
        self.assertEqual(self.mock_task_queue_manager.default_job_timeout, 1800)
    
    def test_update_timeout_settings_invalid_value(self):
        """Test timeout settings update with invalid value"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Set invalid configuration value
        self.config_values['default_job_timeout'] = -100
        
        # Call update method
        result = adapter.update_timeout_settings()
        
        # Verify failure
        self.assertFalse(result)
        # Original value should be preserved
        self.assertEqual(self.mock_task_queue_manager.default_job_timeout, 7200)
    
    def test_update_queue_size_limits_success(self):
        """Test successful queue size limits update"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Update configuration value
        self.config_values['queue_size_limit'] = 500
        
        # Call update method
        result = adapter.update_queue_size_limits()
        
        # Verify success
        self.assertTrue(result)
        self.assertEqual(self.mock_task_queue_manager.queue_size_limit, 500)
    
    def test_update_queue_size_limits_invalid_value(self):
        """Test queue size limits update with invalid value"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Set invalid configuration value
        self.config_values['queue_size_limit'] = 0
        
        # Call update method
        result = adapter.update_queue_size_limits()
        
        # Verify failure
        self.assertFalse(result)
        # Original value should be preserved
        self.assertEqual(self.mock_task_queue_manager.queue_size_limit, 200)
    
    def test_handle_max_concurrent_jobs_change(self):
        """Test handling of max_concurrent_jobs configuration change"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Update configuration value
        self.config_values['max_concurrent_jobs'] = 8
        
        # Simulate configuration change
        adapter._handle_max_concurrent_jobs_change('max_concurrent_jobs', 5, 8)
        
        # Verify task queue manager was updated
        self.assertEqual(self.mock_task_queue_manager.max_concurrent_tasks, 8)
    
    def test_handle_default_job_timeout_change(self):
        """Test handling of default_job_timeout configuration change"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Update configuration value
        self.config_values['default_job_timeout'] = 5400
        
        # Simulate configuration change
        adapter._handle_default_job_timeout_change('default_job_timeout', 7200, 5400)
        
        # Verify task queue manager was updated
        self.assertEqual(self.mock_task_queue_manager.default_job_timeout, 5400)
    
    def test_handle_queue_size_limit_change(self):
        """Test handling of queue_size_limit configuration change"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Update configuration value
        self.config_values['queue_size_limit'] = 300
        
        # Simulate configuration change
        adapter._handle_queue_size_limit_change('queue_size_limit', 200, 300)
        
        # Verify task queue manager was updated
        self.assertEqual(self.mock_task_queue_manager.queue_size_limit, 300)
    
    def test_handle_queue_limit_change_direct(self):
        """Test direct queue limit change handling"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Call direct method
        result = adapter.handle_queue_limit_change(150)
        
        # Verify success
        self.assertTrue(result)
        self.assertEqual(self.mock_task_queue_manager.queue_size_limit, 150)
    
    def test_handle_queue_limit_change_invalid(self):
        """Test direct queue limit change with invalid value"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Call direct method with invalid value
        result = adapter.handle_queue_limit_change(-5)
        
        # Verify failure
        self.assertFalse(result)
        # Original value should be preserved
        self.assertEqual(self.mock_task_queue_manager.queue_size_limit, 200)
    
    def test_get_current_configuration(self):
        """Test getting current configuration values"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        config = adapter.get_current_configuration()
        
        # Verify configuration values
        expected_config = {
            'max_concurrent_jobs': 5,
            'default_job_timeout': 7200,
            'queue_size_limit': 200,
            'current_max_concurrent_tasks': 5,
            'current_default_job_timeout': 7200,
            'current_queue_size_limit': 200
        }
        
        self.assertEqual(config, expected_config)
    
    def test_validate_queue_size_before_enqueue_allowed(self):
        """Test queue size validation when enqueue is allowed"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Current queue has 5 items, limit is 200, so should be allowed
        result = adapter.validate_queue_size_before_enqueue(user_id=123)
        
        self.assertTrue(result)
    
    def test_validate_queue_size_before_enqueue_rejected(self):
        """Test queue size validation when enqueue should be rejected"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Set queue stats to show queue is full
        self.mock_task_queue_manager.get_queue_stats.return_value = {
            'queued': 200,  # At limit
            'running': 2,
            'total': 202
        }
        
        result = adapter.validate_queue_size_before_enqueue(user_id=123)
        
        self.assertFalse(result)
    
    def test_validate_queue_size_before_enqueue_error_handling(self):
        """Test queue size validation with error handling"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Make get_queue_stats raise an exception
        self.mock_task_queue_manager.get_queue_stats.side_effect = Exception("Database error")
        
        # Should fail open (return True) on error
        result = adapter.validate_queue_size_before_enqueue(user_id=123)
        
        self.assertTrue(result)
    
    def test_enforce_queue_size_limit_warning(self):
        """Test queue size limit enforcement with warning"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Set queue stats to show queue exceeds limit
        self.mock_task_queue_manager.get_queue_stats.return_value = {
            'queued': 250,  # Exceeds limit of 200
            'running': 2,
            'total': 252
        }
        
        # Should not raise exception, just log warning
        with patch('task_queue_configuration_adapter.logger') as mock_logger:
            adapter._enforce_queue_size_limit()
            mock_logger.warning.assert_called_once()
    
    def test_cleanup(self):
        """Test adapter cleanup"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Call cleanup
        adapter.cleanup()
        
        # Verify unsubscribe was called for all subscriptions
        expected_unsubscribe_calls = [call("subscription-id-123")] * 3
        self.mock_config_service.unsubscribe.assert_has_calls(
            expected_unsubscribe_calls, any_order=True
        )
    
    def test_configuration_change_with_exception(self):
        """Test configuration change handling with exception"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Make update method raise exception
        with patch.object(adapter, 'update_concurrency_limits', side_effect=Exception("Update failed")):
            # Should not raise exception, just log error
            with patch('task_queue_configuration_adapter.logger') as mock_logger:
                adapter._handle_max_concurrent_jobs_change('max_concurrent_jobs', 5, 8)
                mock_logger.error.assert_called_once()
    
    def test_configuration_service_error_handling(self):
        """Test handling of configuration service errors"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Make config service raise error
        self.mock_config_service.get_config.side_effect = ConfigurationError("Service unavailable")
        
        # Should return False and not crash
        result = adapter.update_concurrency_limits()
        self.assertFalse(result)
    
    def test_thread_safety(self):
        """Test thread safety of adapter operations"""
        adapter = TaskQueueConfigurationAdapter(
            self.mock_task_queue_manager,
            self.mock_config_service
        )
        
        # Verify adapter has lock
        self.assertIsNotNone(adapter._lock)
        
        # Test that methods use the lock (by checking they don't raise exceptions)
        adapter.update_concurrency_limits()
        adapter.update_timeout_settings()
        adapter.update_queue_size_limits()
        adapter.handle_queue_limit_change(150)


if __name__ == '__main__':
    unittest.main()
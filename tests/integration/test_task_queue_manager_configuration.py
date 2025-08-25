# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for TaskQueueManager with ConfigurationService

Tests the integration between TaskQueueManager and ConfigurationService
for dynamic configuration updates.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
from datetime import datetime, timezone, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from task_queue_manager import TaskQueueManager
from configuration_service import ConfigurationService
from task_queue_configuration_adapter import TaskQueueConfigurationAdapter
from models import CaptionGenerationTask, TaskStatus, JobPriority


class TestTaskQueueManagerConfiguration(unittest.TestCase):
    """Integration tests for TaskQueueManager with configuration service"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock DatabaseManager
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Mock ConfigurationService
        self.mock_config_service = Mock()
        self.config_values = {
            'max_concurrent_jobs': 5,
            'default_job_timeout': 7200,
            'queue_size_limit': 200
        }
        self.mock_config_service.get_config.side_effect = self._mock_get_config
        
        # Create TaskQueueManager with configuration service
        self.task_queue_manager = TaskQueueManager(
            db_manager=self.mock_db_manager,
            max_concurrent_tasks=3,  # Fallback value
            config_service=self.mock_config_service
        )
    
    def _mock_get_config(self, key, default=None):
        """Mock configuration service get_config method"""
        return self.config_values.get(key, default)
    
    def test_initialization_with_config_service(self):
        """Test TaskQueueManager initialization with configuration service"""
        # Verify configuration values were read from service
        self.assertEqual(self.task_queue_manager.max_concurrent_tasks, 5)
        self.assertEqual(self.task_queue_manager.default_job_timeout, 7200)
        self.assertEqual(self.task_queue_manager.queue_size_limit, 200)
        
        # Verify config service was called
        expected_calls = [
            ('max_concurrent_jobs', 3),
            ('default_job_timeout', 3600),
            ('queue_size_limit', 100)
        ]
        for key, default in expected_calls:
            self.mock_config_service.get_config.assert_any_call(key, default)
    
    def test_initialization_without_config_service(self):
        """Test TaskQueueManager initialization without configuration service"""
        task_queue_manager = TaskQueueManager(
            db_manager=self.mock_db_manager,
            max_concurrent_tasks=8
        )
        
        # Verify fallback values were used
        self.assertEqual(task_queue_manager.max_concurrent_tasks, 8)
        self.assertEqual(task_queue_manager.default_job_timeout, 3600)
        self.assertEqual(task_queue_manager.queue_size_limit, 100)
    
    def test_update_max_concurrent_tasks_success(self):
        """Test successful update of max concurrent tasks"""
        result = self.task_queue_manager.update_max_concurrent_tasks(10)
        
        self.assertTrue(result)
        self.assertEqual(self.task_queue_manager.max_concurrent_tasks, 10)
    
    def test_update_max_concurrent_tasks_invalid_value(self):
        """Test update of max concurrent tasks with invalid value"""
        original_value = self.task_queue_manager.max_concurrent_tasks
        
        # Test negative value
        result = self.task_queue_manager.update_max_concurrent_tasks(-1)
        self.assertFalse(result)
        self.assertEqual(self.task_queue_manager.max_concurrent_tasks, original_value)
        
        # Test zero value
        result = self.task_queue_manager.update_max_concurrent_tasks(0)
        self.assertFalse(result)
        self.assertEqual(self.task_queue_manager.max_concurrent_tasks, original_value)
        
        # Test non-integer value
        result = self.task_queue_manager.update_max_concurrent_tasks("invalid")
        self.assertFalse(result)
        self.assertEqual(self.task_queue_manager.max_concurrent_tasks, original_value)
    
    def test_update_default_job_timeout_success(self):
        """Test successful update of default job timeout"""
        result = self.task_queue_manager.update_default_job_timeout(1800)
        
        self.assertTrue(result)
        self.assertEqual(self.task_queue_manager.default_job_timeout, 1800)
    
    def test_update_default_job_timeout_invalid_value(self):
        """Test update of default job timeout with invalid value"""
        original_value = self.task_queue_manager.default_job_timeout
        
        # Test negative value
        result = self.task_queue_manager.update_default_job_timeout(-100)
        self.assertFalse(result)
        self.assertEqual(self.task_queue_manager.default_job_timeout, original_value)
        
        # Test zero value
        result = self.task_queue_manager.update_default_job_timeout(0)
        self.assertFalse(result)
        self.assertEqual(self.task_queue_manager.default_job_timeout, original_value)
    
    def test_update_queue_size_limit_success(self):
        """Test successful update of queue size limit"""
        result = self.task_queue_manager.update_queue_size_limit(500)
        
        self.assertTrue(result)
        self.assertEqual(self.task_queue_manager.queue_size_limit, 500)
    
    def test_update_queue_size_limit_invalid_value(self):
        """Test update of queue size limit with invalid value"""
        original_value = self.task_queue_manager.queue_size_limit
        
        # Test negative value
        result = self.task_queue_manager.update_queue_size_limit(-10)
        self.assertFalse(result)
        self.assertEqual(self.task_queue_manager.queue_size_limit, original_value)
        
        # Test zero value
        result = self.task_queue_manager.update_queue_size_limit(0)
        self.assertFalse(result)
        self.assertEqual(self.task_queue_manager.queue_size_limit, original_value)
    
    def test_get_configuration_values(self):
        """Test getting current configuration values"""
        config = self.task_queue_manager.get_configuration_values()
        
        expected_config = {
            'max_concurrent_tasks': 5,
            'default_job_timeout': 7200,
            'queue_size_limit': 200
        }
        
        self.assertEqual(config, expected_config)
    
    def test_refresh_configuration_success(self):
        """Test successful configuration refresh"""
        # Update configuration values
        self.config_values['max_concurrent_jobs'] = 8
        self.config_values['default_job_timeout'] = 5400
        self.config_values['queue_size_limit'] = 300
        
        result = self.task_queue_manager.refresh_configuration()
        
        self.assertTrue(result)
        self.assertEqual(self.task_queue_manager.max_concurrent_tasks, 8)
        self.assertEqual(self.task_queue_manager.default_job_timeout, 5400)
        self.assertEqual(self.task_queue_manager.queue_size_limit, 300)
    
    def test_refresh_configuration_without_service(self):
        """Test configuration refresh without configuration service"""
        task_queue_manager = TaskQueueManager(
            db_manager=self.mock_db_manager,
            max_concurrent_tasks=3
        )
        
        result = task_queue_manager.refresh_configuration()
        
        self.assertFalse(result)
    
    def test_enqueue_task_with_queue_size_limit(self):
        """Test task enqueue with queue size limit enforcement"""
        # Mock task
        mock_task = Mock()
        mock_task.id = None
        mock_task.user_id = 123
        mock_task.priority = None
        
        # Mock security manager
        with patch('security.features.caption_security.CaptionSecurityManager') as mock_security_class:
            mock_security = Mock()
            mock_security.generate_secure_task_id.return_value = "task-123"
            mock_security_class.return_value = mock_security
            
            # Mock database queries
            self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = None
            self.mock_session.query.return_value.filter_by.return_value.count.return_value = 50  # Under limit
            
            # Should succeed
            result = self.task_queue_manager.enqueue_task(mock_task)
            
            self.assertEqual(result, "task-123")
            self.mock_session.add.assert_called_once_with(mock_task)
            self.mock_session.commit.assert_called_once()
    
    def test_enqueue_task_queue_size_limit_exceeded(self):
        """Test task enqueue when queue size limit is exceeded"""
        # Mock task
        mock_task = Mock()
        mock_task.id = None
        mock_task.user_id = 123
        mock_task.priority = None
        
        # Mock security manager
        with patch('security.features.caption_security.CaptionSecurityManager') as mock_security_class:
            mock_security = Mock()
            mock_security.generate_secure_task_id.return_value = "task-123"
            mock_security_class.return_value = mock_security
            
            # Mock database queries
            self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = None
            self.mock_session.query.return_value.filter_by.return_value.count.return_value = 200  # At limit
            
            # Should raise ValueError
            with self.assertRaises(ValueError) as context:
                self.task_queue_manager.enqueue_task(mock_task)
            
            self.assertIn("Queue size limit reached", str(context.exception))
            self.mock_session.add.assert_not_called()
    
    def test_enforce_job_timeout_within_limit(self):
        """Test job timeout enforcement when task is within timeout"""
        # Mock task
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_task.status = TaskStatus.RUNNING
        mock_task.started_at = datetime.now(timezone.utc) - timedelta(seconds=1800)  # 30 minutes ago
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.task_queue_manager.enforce_job_timeout("task-123")
        
        self.assertTrue(result)
        # Task should not be modified
        self.assertEqual(mock_task.status, TaskStatus.RUNNING)
    
    def test_enforce_job_timeout_exceeded(self):
        """Test job timeout enforcement when task has exceeded timeout"""
        # Mock task that started 3 hours ago (exceeds 2 hour timeout)
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_task.status = TaskStatus.RUNNING
        mock_task.started_at = datetime.now(timezone.utc) - timedelta(seconds=10800)  # 3 hours ago
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.task_queue_manager.enforce_job_timeout("task-123")
        
        self.assertTrue(result)
        # Task should be marked as failed
        self.assertEqual(mock_task.status, TaskStatus.FAILED)
        self.assertIsNotNone(mock_task.completed_at)
        self.assertIn("timed out", mock_task.error_message)
        self.mock_session.commit.assert_called_once()
    
    def test_enforce_job_timeout_task_not_found(self):
        """Test job timeout enforcement when task is not found"""
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.task_queue_manager.enforce_job_timeout("nonexistent-task")
        
        self.assertTrue(result)  # Should return True for non-existent tasks
    
    def test_enforce_job_timeout_task_not_running(self):
        """Test job timeout enforcement when task is not running"""
        # Mock completed task
        mock_task = Mock()
        mock_task.status = TaskStatus.COMPLETED
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        result = self.task_queue_manager.enforce_job_timeout("task-123")
        
        self.assertTrue(result)  # Should return True for non-running tasks
    
    def test_enforce_job_timeout_no_timeout_configured(self):
        """Test job timeout enforcement when no timeout is configured"""
        # Create task queue manager without timeout
        task_queue_manager = TaskQueueManager(
            db_manager=self.mock_db_manager,
            max_concurrent_tasks=3
        )
        delattr(task_queue_manager, 'default_job_timeout')
        
        result = task_queue_manager.enforce_job_timeout("task-123")
        
        self.assertTrue(result)  # Should return True when no timeout configured
    
    def test_integration_with_adapter(self):
        """Test integration with TaskQueueConfigurationAdapter"""
        # Create adapter
        adapter = TaskQueueConfigurationAdapter(
            self.task_queue_manager,
            self.mock_config_service
        )
        
        # Verify adapter initialized correctly
        self.assertIsNotNone(adapter)
        
        # Test configuration update through adapter
        self.config_values['max_concurrent_jobs'] = 12
        result = adapter.update_concurrency_limits()
        
        self.assertTrue(result)
        self.assertEqual(self.task_queue_manager.max_concurrent_tasks, 12)
    
    def test_thread_safety(self):
        """Test thread safety of configuration updates"""
        import threading
        import time
        
        results = []
        
        def update_config():
            result = self.task_queue_manager.update_max_concurrent_tasks(15)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_config)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all updates succeeded
        self.assertEqual(len(results), 5)
        self.assertTrue(all(results))
        self.assertEqual(self.task_queue_manager.max_concurrent_tasks, 15)


if __name__ == '__main__':
    unittest.main()
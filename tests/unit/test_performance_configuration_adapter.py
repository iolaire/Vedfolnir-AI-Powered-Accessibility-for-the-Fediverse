# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Performance Configuration Adapter

Tests memory usage limit enforcement, job priority weight system,
and performance configuration validation.
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

from performance_configuration_adapter import (
    PerformanceConfigurationAdapter, 
    MemoryLimitExceededError,
    PerformanceConfigurationError,
    MemoryUsageInfo,
    PriorityWeights
)
from models import JobPriority


class TestPriorityWeights(unittest.TestCase):
    """Test PriorityWeights data class"""
    
    def test_from_dict(self):
        """Test creating PriorityWeights from dictionary"""
        data = {"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        weights = PriorityWeights.from_dict(data)
        
        self.assertEqual(weights.urgent, 4.0)
        self.assertEqual(weights.high, 3.0)
        self.assertEqual(weights.normal, 2.0)
        self.assertEqual(weights.low, 1.0)
    
    def test_from_dict_with_defaults(self):
        """Test creating PriorityWeights with missing values"""
        data = {"urgent": 5.0, "normal": 1.5}
        weights = PriorityWeights.from_dict(data)
        
        self.assertEqual(weights.urgent, 5.0)
        self.assertEqual(weights.high, 3.0)  # Default
        self.assertEqual(weights.normal, 1.5)
        self.assertEqual(weights.low, 1.0)  # Default
    
    def test_to_dict(self):
        """Test converting PriorityWeights to dictionary"""
        weights = PriorityWeights(urgent=4.0, high=3.0, normal=2.0, low=1.0)
        data = weights.to_dict()
        
        expected = {"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        self.assertEqual(data, expected)


class TestPerformanceConfigurationAdapter(unittest.TestCase):
    """Test PerformanceConfigurationAdapter"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_task_queue = Mock()
        self.mock_config_service = Mock()
        
        # Mock configuration service methods
        self.mock_config_service.get_config.side_effect = self._mock_get_config
        self.mock_config_service.subscribe_to_changes.return_value = "test-subscription-id"
        
        # Default configuration values
        self.config_values = {
            "max_memory_usage_mb": 2048,
            "processing_priority_weights": {"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        }
        
        self.adapter = PerformanceConfigurationAdapter(
            self.mock_task_queue,
            self.mock_config_service
        )
    
    def _mock_get_config(self, key, default=None):
        """Mock configuration service get_config method"""
        return self.config_values.get(key, default)
    
    def test_initialization(self):
        """Test adapter initialization"""
        self.assertIsNotNone(self.adapter)
        self.assertEqual(self.adapter._current_memory_limit_mb, 2048)
        self.assertEqual(self.adapter._current_priority_weights.urgent, 4.0)
        
        # Verify subscriptions were set up
        self.assertEqual(self.mock_config_service.subscribe_to_changes.call_count, 2)
    
    def test_update_memory_limits_success(self):
        """Test successful memory limit update"""
        self.config_values["max_memory_usage_mb"] = 4096
        
        result = self.adapter.update_memory_limits()
        
        self.assertTrue(result)
        self.assertEqual(self.adapter._current_memory_limit_mb, 4096)
    
    def test_update_memory_limits_invalid_value(self):
        """Test memory limit update with invalid value"""
        self.config_values["max_memory_usage_mb"] = 256  # Below minimum
        
        result = self.adapter.update_memory_limits()
        
        self.assertFalse(result)
        # Should keep old value
        self.assertEqual(self.adapter._current_memory_limit_mb, 2048)
    
    def test_update_memory_limits_non_integer(self):
        """Test memory limit update with non-integer value"""
        self.config_values["max_memory_usage_mb"] = "invalid"
        
        result = self.adapter.update_memory_limits()
        
        self.assertFalse(result)
        self.assertEqual(self.adapter._current_memory_limit_mb, 2048)
    
    def test_update_priority_weights_success(self):
        """Test successful priority weights update"""
        new_weights = {"urgent": 5.0, "high": 4.0, "normal": 2.0, "low": 0.5}
        self.config_values["processing_priority_weights"] = new_weights
        
        result = self.adapter.update_priority_weights()
        
        self.assertTrue(result)
        self.assertEqual(self.adapter._current_priority_weights.urgent, 5.0)
        self.assertEqual(self.adapter._current_priority_weights.low, 0.5)
    
    def test_update_priority_weights_invalid_format(self):
        """Test priority weights update with invalid format"""
        self.config_values["processing_priority_weights"] = "invalid"
        
        result = self.adapter.update_priority_weights()
        
        self.assertFalse(result)
        # Should keep old values
        self.assertEqual(self.adapter._current_priority_weights.urgent, 4.0)
    
    def test_update_priority_weights_negative_values(self):
        """Test priority weights update with negative values"""
        new_weights = {"urgent": -1.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        self.config_values["processing_priority_weights"] = new_weights
        
        result = self.adapter.update_priority_weights()
        
        self.assertFalse(result)
        self.assertEqual(self.adapter._current_priority_weights.urgent, 4.0)
    
    @patch('psutil.Process')
    def test_check_memory_usage_success(self, mock_process_class):
        """Test successful memory usage check"""
        # Mock process memory info
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 1024  # 1GB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        usage_info = self.adapter.check_memory_usage()
        
        self.assertIsInstance(usage_info, MemoryUsageInfo)
        self.assertEqual(usage_info.current_mb, 1024.0)
        self.assertEqual(usage_info.limit_mb, 2048)
        self.assertEqual(usage_info.percentage, 50.0)
    
    @patch('psutil.Process')
    def test_check_memory_usage_process_not_found(self, mock_process_class):
        """Test memory usage check with non-existent process"""
        import psutil
        mock_process_class.side_effect = psutil.NoSuchProcess(123)
        
        with self.assertRaises(PerformanceConfigurationError):
            self.adapter.check_memory_usage(123)
    
    @patch('psutil.Process')
    def test_enforce_memory_limit_within_limits(self, mock_process_class):
        """Test memory limit enforcement when within limits"""
        # Mock process using 1GB (within 2GB limit)
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 1024  # 1GB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        result = self.adapter.enforce_memory_limit()
        
        self.assertTrue(result)
    
    @patch('psutil.Process')
    def test_enforce_memory_limit_exceeded(self, mock_process_class):
        """Test memory limit enforcement when limit exceeded"""
        # Mock process using 3GB (exceeds 2GB limit)
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 3 * 1024 * 1024 * 1024  # 3GB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        with self.assertRaises(MemoryLimitExceededError) as context:
            self.adapter.enforce_memory_limit(task_id="test-task")
        
        self.assertIn("Memory limit exceeded", str(context.exception))
        self.assertIn("test-task", str(context.exception))
    
    def test_get_priority_score(self):
        """Test getting priority scores for different job priorities"""
        self.assertEqual(self.adapter.get_priority_score(JobPriority.URGENT), 4.0)
        self.assertEqual(self.adapter.get_priority_score(JobPriority.HIGH), 3.0)
        self.assertEqual(self.adapter.get_priority_score(JobPriority.NORMAL), 2.0)
        self.assertEqual(self.adapter.get_priority_score(JobPriority.LOW), 1.0)
    
    def test_validate_performance_configuration_valid(self):
        """Test validation with valid configuration"""
        config = {
            "max_memory_usage_mb": 1024,
            "processing_priority_weights": {"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0},
            "max_concurrent_jobs": 2
        }
        
        errors = self.adapter.validate_performance_configuration(config)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_performance_configuration_invalid_memory(self):
        """Test validation with invalid memory limit"""
        config = {
            "max_memory_usage_mb": 256,  # Below minimum
            "processing_priority_weights": {"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        }
        
        errors = self.adapter.validate_performance_configuration(config)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("must be at least 512MB" in error for error in errors))
    
    def test_validate_performance_configuration_invalid_priority_weights(self):
        """Test validation with invalid priority weights"""
        config = {
            "max_memory_usage_mb": 1024,
            "processing_priority_weights": {"urgent": -1.0, "high": 3.0}  # Missing keys and negative value
        }
        
        errors = self.adapter.validate_performance_configuration(config)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("missing required key" in error for error in errors))
        self.assertTrue(any("must be positive" in error for error in errors))
    
    def test_validate_performance_configuration_memory_vs_jobs_warning(self):
        """Test validation warning for high total memory usage"""
        config = {
            "max_memory_usage_mb": 8192,  # 8GB per job
            "max_concurrent_jobs": 8,     # 8 jobs = 64GB total
            "processing_priority_weights": {"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        }
        
        errors = self.adapter.validate_performance_configuration(config)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("may exceed system capacity" in error for error in errors))
    
    def test_memory_limit_change_handler(self):
        """Test memory limit configuration change handler"""
        # Update the mock configuration values first
        self.config_values["max_memory_usage_mb"] = 4096
        
        # Simulate configuration change
        self.adapter._handle_memory_limit_change("max_memory_usage_mb", 2048, 4096)
        
        # Should have updated the memory limit
        self.assertEqual(self.adapter._current_memory_limit_mb, 4096)
    
    def test_priority_weights_change_handler(self):
        """Test priority weights configuration change handler"""
        new_weights = {"urgent": 5.0, "high": 4.0, "normal": 2.0, "low": 1.0}
        self.config_values["processing_priority_weights"] = new_weights
        
        # Simulate configuration change
        self.adapter._handle_priority_weights_change("processing_priority_weights", {}, new_weights)
        
        # Should have updated the priority weights
        self.assertEqual(self.adapter._current_priority_weights.urgent, 5.0)
    
    @patch('psutil.Process')
    def test_get_memory_usage_history(self, mock_process_class):
        """Test memory usage history tracking"""
        # Mock process memory info
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 1024  # 1GB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        # Generate some memory usage data
        for _ in range(5):
            self.adapter.check_memory_usage()
        
        history = self.adapter.get_memory_usage_history()
        
        self.assertEqual(len(history), 5)
        self.assertIsInstance(history[0], MemoryUsageInfo)
    
    def test_get_current_configuration(self):
        """Test getting current configuration"""
        config = self.adapter.get_current_configuration()
        
        self.assertIn('max_memory_usage_mb', config)
        self.assertIn('processing_priority_weights', config)
        self.assertEqual(config['max_memory_usage_mb'], 2048)
    
    @patch('psutil.Process')
    def test_get_performance_stats(self, mock_process_class):
        """Test getting performance statistics"""
        # Mock process memory info
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 1024  # 1GB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        # Mock task queue stats
        self.mock_task_queue.get_queue_stats.return_value = {'queued': 5, 'running': 2}
        
        stats = self.adapter.get_performance_stats()
        
        self.assertIn('current_memory', stats)
        self.assertIn('priority_weights', stats)
        self.assertIn('queue_stats', stats)
        self.assertEqual(stats['queue_stats']['queued'], 5)
    
    def test_cleanup(self):
        """Test adapter cleanup"""
        # Add some memory usage history
        self.adapter._memory_usage_history = [Mock(), Mock(), Mock()]
        
        self.adapter.cleanup()
        
        # Should have unsubscribed from configuration changes
        self.mock_config_service.unsubscribe.assert_called()
        
        # Should have cleared memory usage history
        self.assertEqual(len(self.adapter._memory_usage_history), 0)


class TestPerformanceConfigurationIntegration(unittest.TestCase):
    """Integration tests for performance configuration"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_task_queue = Mock()
        self.mock_config_service = Mock()
        
        # Mock configuration values
        self.config_values = {
            "max_memory_usage_mb": 1024,
            "processing_priority_weights": {"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0}
        }
        
        self.mock_config_service.get_config.side_effect = lambda key, default=None: self.config_values.get(key, default)
        self.mock_config_service.subscribe_to_changes.return_value = "test-subscription"
    
    def test_configuration_change_propagation(self):
        """Test that configuration changes propagate correctly"""
        adapter = PerformanceConfigurationAdapter(self.mock_task_queue, self.mock_config_service)
        
        # Verify initial values
        self.assertEqual(adapter._current_memory_limit_mb, 1024)
        
        # Change configuration
        self.config_values["max_memory_usage_mb"] = 2048
        
        # Simulate configuration change notification
        adapter._handle_memory_limit_change("max_memory_usage_mb", 1024, 2048)
        
        # Verify change was applied
        self.assertEqual(adapter._current_memory_limit_mb, 2048)
    
    def test_priority_weight_system_integration(self):
        """Test priority weight system integration"""
        adapter = PerformanceConfigurationAdapter(self.mock_task_queue, self.mock_config_service)
        
        # Test different priority scores
        urgent_score = adapter.get_priority_score(JobPriority.URGENT)
        normal_score = adapter.get_priority_score(JobPriority.NORMAL)
        low_score = adapter.get_priority_score(JobPriority.LOW)
        
        # Verify priority ordering
        self.assertGreater(urgent_score, normal_score)
        self.assertGreater(normal_score, low_score)
        
        # Change priority weights
        new_weights = {"urgent": 10.0, "high": 5.0, "normal": 2.0, "low": 0.1}
        self.config_values["processing_priority_weights"] = new_weights
        
        # Apply change
        adapter._handle_priority_weights_change("processing_priority_weights", {}, new_weights)
        
        # Verify new scores
        new_urgent_score = adapter.get_priority_score(JobPriority.URGENT)
        new_low_score = adapter.get_priority_score(JobPriority.LOW)
        
        self.assertEqual(new_urgent_score, 10.0)
        self.assertEqual(new_low_score, 0.1)


if __name__ == '__main__':
    unittest.main()
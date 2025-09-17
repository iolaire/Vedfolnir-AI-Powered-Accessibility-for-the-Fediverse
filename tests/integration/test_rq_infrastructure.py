# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for RQ infrastructure setup.

Tests the basic RQ configuration, Redis connection management, and health monitoring
components to ensure they work correctly together.
"""

import unittest
import os
import sys
import time
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.task.rq import (
    RQConfig, 
    WorkerMode, 
    TaskPriority, 
    RedisHealthMonitor, 
    RedisConnectionManager,
    rq_config
)


class TestRQInfrastructure(unittest.TestCase):
    """Test RQ infrastructure components"""
    
    def setUp(self):
        """Set up test environment"""
        # Set test environment variables
        os.environ.update({
            'REDIS_URL': 'redis://localhost:6379/1',  # Use test DB
            'WORKER_MODE': 'integrated',
            'RQ_WORKER_COUNT': '2',
            'RQ_WORKER_TIMEOUT': '300',
            'RQ_WORKER_MEMORY_LIMIT': '500',
            'RQ_QUEUE_PREFIX': 'test:rq:',
            'RQ_HEALTH_CHECK_INTERVAL': '5',
            'REDIS_MEMORY_THRESHOLD': '0.8',
            'RQ_FAILURE_THRESHOLD': '3'
        })
        
        # Create fresh config for testing
        self.config = RQConfig()
    
    def tearDown(self):
        """Clean up test environment"""
        # Clean up environment variables
        test_vars = [
            'REDIS_URL', 'WORKER_MODE', 'RQ_WORKER_COUNT', 'RQ_WORKER_TIMEOUT',
            'RQ_WORKER_MEMORY_LIMIT', 'RQ_QUEUE_PREFIX', 'RQ_HEALTH_CHECK_INTERVAL',
            'REDIS_MEMORY_THRESHOLD', 'RQ_FAILURE_THRESHOLD'
        ]
        for var in test_vars:
            os.environ.pop(var, None)
    
    def test_rq_config_initialization(self):
        """Test RQ configuration initialization"""
        self.assertEqual(self.config.redis_url, 'redis://localhost:6379/1')
        self.assertEqual(self.config.worker_mode, WorkerMode.INTEGRATED)
        self.assertEqual(self.config.worker_count, 2)
        self.assertEqual(self.config.worker_timeout, 300)
        self.assertEqual(self.config.worker_memory_limit, 500)
        self.assertEqual(self.config.queue_prefix, 'test:rq:')
        self.assertEqual(self.config.health_check_interval, 5)
        self.assertEqual(self.config.redis_memory_threshold, 0.8)
        self.assertEqual(self.config.failure_threshold, 3)
    
    def test_queue_configurations(self):
        """Test queue configurations are properly initialized"""
        queue_configs = self.config.queue_configs
        
        # Check all priority queues exist
        expected_queues = [
            TaskPriority.URGENT.value,
            TaskPriority.HIGH.value,
            TaskPriority.NORMAL.value,
            TaskPriority.LOW.value
        ]
        
        for queue_name in expected_queues:
            self.assertIn(queue_name, queue_configs)
            queue_config = queue_configs[queue_name]
            self.assertTrue(queue_config.name.startswith('test:rq:'))
            self.assertIsInstance(queue_config.priority_level, int)
            self.assertGreater(queue_config.max_workers, 0)
            self.assertGreater(queue_config.timeout, 0)
    
    def test_worker_configurations(self):
        """Test worker configurations for integrated mode"""
        worker_configs = self.config.worker_configs
        
        # Should have integrated workers for integrated mode
        self.assertIn('integrated_urgent_high', worker_configs)
        self.assertIn('integrated_normal', worker_configs)
        
        urgent_high_config = worker_configs['integrated_urgent_high']
        self.assertEqual(urgent_high_config.queues, ['urgent', 'high'])
        self.assertEqual(urgent_high_config.concurrency, 2)
        self.assertEqual(urgent_high_config.memory_limit, 500)
        
        normal_config = worker_configs['integrated_normal']
        self.assertEqual(normal_config.queues, ['normal'])
        self.assertEqual(normal_config.concurrency, 2)
    
    def test_redis_connection_params(self):
        """Test Redis connection parameter parsing"""
        params = self.config.get_redis_connection_params()
        
        self.assertEqual(params['host'], 'localhost')
        self.assertEqual(params['port'], 6379)
        self.assertEqual(params['db'], 1)
        self.assertTrue(params['decode_responses'])
        self.assertEqual(params['socket_connect_timeout'], 5)
        self.assertEqual(params['socket_timeout'], 5)
        self.assertTrue(params['retry_on_timeout'])
        self.assertEqual(params['health_check_interval'], 30)
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid configuration should pass
        self.assertTrue(self.config.validate_config())
        
        # Test invalid worker count
        original_count = self.config.worker_count
        self.config.worker_count = 0
        self.assertFalse(self.config.validate_config())
        self.config.worker_count = original_count
        
        # Test invalid timeout
        original_timeout = self.config.worker_timeout
        self.config.worker_timeout = 30  # Too low
        self.assertFalse(self.config.validate_config())
        self.config.worker_timeout = original_timeout
        
        # Test invalid memory limit
        original_memory = self.config.worker_memory_limit
        self.config.worker_memory_limit = 50  # Too low
        self.assertFalse(self.config.validate_config())
        self.config.worker_memory_limit = original_memory
    
    def test_config_to_dict(self):
        """Test configuration serialization to dictionary"""
        config_dict = self.config.to_dict()
        
        # Check required keys exist
        required_keys = [
            'redis_url', 'redis_db', 'worker_mode', 'worker_count',
            'worker_timeout', 'worker_memory_limit', 'queue_prefix',
            'default_timeout', 'result_ttl', 'job_ttl', 'health_check_interval',
            'redis_memory_threshold', 'failure_threshold', 'queue_configs',
            'worker_configs'
        ]
        
        for key in required_keys:
            self.assertIn(key, config_dict)
        
        # Check worker mode is serialized as string
        self.assertEqual(config_dict['worker_mode'], 'integrated')
    
    @patch('redis.Redis')
    def test_redis_connection_manager_initialization(self, mock_redis_class):
        """Test Redis connection manager initialization"""
        # Mock Redis connection
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        
        # Mock connection pool
        with patch('redis.connection.ConnectionPool') as mock_pool_class:
            mock_pool = Mock()
            mock_pool_class.return_value = mock_pool
            
            connection_manager = RedisConnectionManager(self.config)
            result = connection_manager.initialize()
            
            self.assertTrue(result)
            self.assertIsNotNone(connection_manager._connection_pool)
            self.assertIsNotNone(connection_manager._redis_connection)
            self.assertIsNotNone(connection_manager._health_monitor)
    
    @patch('redis.Redis')
    def test_redis_health_monitor_initialization(self, mock_redis_class):
        """Test Redis health monitor initialization"""
        # Mock Redis connection
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {
            'used_memory': 1000000,
            'maxmemory': 10000000,
            'used_memory_human': '1MB',
            'maxmemory_human': '10MB',
            'mem_fragmentation_ratio': 1.2,
            'used_memory_rss': 1200000,
            'connected_clients': 5,
            'client_recent_max_input_buffer': 1024,
            'client_recent_max_output_buffer': 2048,
            'blocked_clients': 0
        }
        mock_redis_class.return_value = mock_redis
        
        health_monitor = RedisHealthMonitor(mock_redis, self.config)
        
        # Test health check
        result = health_monitor.check_health()
        self.assertTrue(result)
        self.assertTrue(health_monitor.is_healthy)
        
        # Test health status
        status = health_monitor.get_health_status()
        self.assertIn('is_healthy', status)
        self.assertIn('consecutive_failures', status)
        self.assertIn('metrics', status)
        
        # Test memory usage
        memory_usage = health_monitor.get_memory_usage()
        self.assertIn('used_memory', memory_usage)
        self.assertIn('used_memory_percentage', memory_usage)
    
    @patch('redis.Redis')
    def test_redis_health_monitor_failure_detection(self, mock_redis_class):
        """Test Redis health monitor failure detection"""
        # Mock Redis connection that fails
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        mock_redis.info.side_effect = Exception("Connection failed")
        mock_redis_class.return_value = mock_redis
        
        health_monitor = RedisHealthMonitor(mock_redis, self.config)
        
        # Test multiple failures to trigger failure threshold
        for i in range(self.config.failure_threshold):
            result = health_monitor.check_health()
            self.assertFalse(result)
        
        # Should be marked as unhealthy after threshold failures
        self.assertFalse(health_monitor.is_healthy)
        self.assertEqual(health_monitor.consecutive_failures, self.config.failure_threshold)
    
    @patch('redis.Redis')
    def test_redis_health_monitor_recovery(self, mock_redis_class):
        """Test Redis health monitor recovery detection"""
        # Mock Redis connection
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        health_monitor = RedisHealthMonitor(mock_redis, self.config)
        
        # Simulate failure
        mock_redis.ping.side_effect = Exception("Connection failed")
        mock_redis.info.side_effect = Exception("Connection failed")
        for i in range(self.config.failure_threshold):
            health_monitor.check_health()
        
        self.assertFalse(health_monitor.is_healthy)
        
        # Simulate recovery
        mock_redis.ping.side_effect = None
        mock_redis.ping.return_value = True
        mock_redis.info.side_effect = None
        mock_redis.info.return_value = {
            'used_memory': 1000000,
            'maxmemory': 10000000,
            'used_memory_human': '1MB',
            'maxmemory_human': '10MB',
            'mem_fragmentation_ratio': 1.2,
            'used_memory_rss': 1200000,
            'connected_clients': 5,
            'client_recent_max_input_buffer': 1024,
            'client_recent_max_output_buffer': 2048,
            'blocked_clients': 0
        }
        
        result = health_monitor.check_health()
        self.assertTrue(result)
        self.assertTrue(health_monitor.is_healthy)
        self.assertEqual(health_monitor.consecutive_failures, 0)
    
    def test_global_config_instance(self):
        """Test global configuration instance"""
        # Test that global config is accessible
        self.assertIsInstance(rq_config, RQConfig)
        self.assertTrue(rq_config.validate_config())
    
    def test_worker_mode_enum(self):
        """Test WorkerMode enum values"""
        self.assertEqual(WorkerMode.INTEGRATED.value, 'integrated')
        self.assertEqual(WorkerMode.EXTERNAL.value, 'external')
        self.assertEqual(WorkerMode.HYBRID.value, 'hybrid')
    
    def test_task_priority_enum(self):
        """Test TaskPriority enum values"""
        self.assertEqual(TaskPriority.URGENT.value, 'urgent')
        self.assertEqual(TaskPriority.HIGH.value, 'high')
        self.assertEqual(TaskPriority.NORMAL.value, 'normal')
        self.assertEqual(TaskPriority.LOW.value, 'low')
    
    def test_queue_names_priority_order(self):
        """Test queue names are returned in priority order"""
        queue_names = self.config.get_queue_names()
        expected_order = ['urgent', 'high', 'normal', 'low']
        self.assertEqual(queue_names, expected_order)


if __name__ == '__main__':
    unittest.main()
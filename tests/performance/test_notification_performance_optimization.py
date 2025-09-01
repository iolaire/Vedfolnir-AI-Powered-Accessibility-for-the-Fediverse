# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Performance Optimization Tests

This module tests the performance optimization components for the notification system,
including WebSocket connection management, notification batching and throttling,
memory management, database query optimization, and caching strategies.
"""

import unittest
import time
import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from notification_performance_optimizer import (
    NotificationPerformanceOptimizer, OptimizationLevel, NotificationCache,
    NotificationBatcher, NotificationThrottler, MemoryManager,
    BatchConfiguration, ThrottleConfiguration, CacheConfiguration, MemoryConfiguration
)
from websocket_connection_optimizer import (
    WebSocketConnectionOptimizer, ConnectionPool, ConnectionPoolConfig,
    ResourceLimits, ConnectionState, ConnectionPriority
)
from notification_database_optimizer import (
    NotificationDatabaseOptimizer, DatabaseOptimizationConfig,
    QueryCache, BatchProcessor, QueryPerformanceMonitor, QueryType
)
from unified_notification_manager import NotificationMessage, NotificationType, NotificationPriority, NotificationCategory
from notification_message_router import NotificationMessageRouter
from notification_persistence_manager import NotificationPersistenceManager


class TestNotificationCache(unittest.TestCase):
    """Test notification caching functionality"""
    
    def setUp(self):
        self.config = CacheConfiguration(
            max_cache_size=100,
            ttl_seconds=60,
            compression_enabled=True
        )
        self.cache = NotificationCache(self.config)
    
    def test_cache_put_and_get(self):
        """Test basic cache put and get operations"""
        message = NotificationMessage(
            id="test_msg_1",
            type=NotificationType.INFO,
            title="Test Message",
            message="Test content",
            user_id=1
        )
        
        # Put message in cache
        self.cache.put(message, user_id=1)
        
        # Get message from cache
        cached_message = self.cache.get("test_msg_1", user_id=1)
        
        self.assertIsNotNone(cached_message)
        self.assertEqual(cached_message.id, "test_msg_1")
        self.assertEqual(cached_message.title, "Test Message")
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        # Use short TTL for testing
        config = CacheConfiguration(ttl_seconds=1)
        cache = NotificationCache(config)
        
        message = NotificationMessage(
            id="test_msg_ttl",
            type=NotificationType.INFO,
            title="TTL Test",
            message="Test content"
        )
        
        cache.put(message)
        
        # Should be available immediately
        cached = cache.get("test_msg_ttl")
        self.assertIsNotNone(cached)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        cached = cache.get("test_msg_ttl")
        self.assertIsNone(cached)
    
    def test_cache_eviction(self):
        """Test cache eviction when full"""
        config = CacheConfiguration(max_cache_size=2)
        cache = NotificationCache(config)
        
        # Add messages to fill cache
        for i in range(3):
            message = NotificationMessage(
                id=f"test_msg_{i}",
                type=NotificationType.INFO,
                title=f"Message {i}",
                message="Test content"
            )
            cache.put(message)
        
        # First message should be evicted
        cached = cache.get("test_msg_0")
        self.assertIsNone(cached)
        
        # Last two should still be available
        cached = cache.get("test_msg_1")
        self.assertIsNotNone(cached)
        cached = cache.get("test_msg_2")
        self.assertIsNotNone(cached)
    
    def test_cache_stats(self):
        """Test cache statistics tracking"""
        message = NotificationMessage(
            id="test_stats",
            type=NotificationType.INFO,
            title="Stats Test",
            message="Test content"
        )
        
        # Initial stats
        stats = self.cache.get_stats()
        initial_hits = stats['stats']['hits']
        initial_misses = stats['stats']['misses']
        
        # Cache miss
        self.cache.get("nonexistent")
        
        # Cache put and hit
        self.cache.put(message)
        self.cache.get("test_stats")
        
        # Check updated stats
        stats = self.cache.get_stats()
        self.assertEqual(stats['stats']['hits'], initial_hits + 1)
        self.assertEqual(stats['stats']['misses'], initial_misses + 1)


class TestNotificationBatcher(unittest.TestCase):
    """Test notification batching functionality"""
    
    def setUp(self):
        self.config = BatchConfiguration(
            max_batch_size=3,
            batch_timeout_ms=100,
            compression_enabled=True
        )
        self.mock_router = Mock(spec=NotificationMessageRouter)
        self.batcher = NotificationBatcher(self.config, self.mock_router)
    
    def test_batch_size_trigger(self):
        """Test batch processing when size limit is reached"""
        messages = []
        for i in range(3):
            message = NotificationMessage(
                id=f"batch_msg_{i}",
                type=NotificationType.INFO,
                title=f"Batch Message {i}",
                message="Test content"
            )
            messages.append(message)
            self.batcher.add_message(message, user_id=1)
        
        # Give time for batch processing
        time.sleep(0.1)
        
        # Check that router was called
        self.assertTrue(self.mock_router.route_user_message.called)
        
        # Check stats
        stats = self.batcher.get_stats()
        self.assertEqual(stats['stats']['messages_batched'], 3)
    
    def test_batch_timeout_trigger(self):
        """Test batch processing when timeout is reached"""
        message = NotificationMessage(
            id="timeout_msg",
            type=NotificationType.INFO,
            title="Timeout Message",
            message="Test content"
        )
        
        self.batcher.add_message(message, user_id=1)
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Check that router was called
        self.assertTrue(self.mock_router.route_user_message.called)
    
    def test_flush_all_batches(self):
        """Test flushing all pending batches"""
        # Add messages to different batches
        for i in range(2):
            message = NotificationMessage(
                id=f"flush_msg_{i}",
                type=NotificationType.INFO,
                title=f"Flush Message {i}",
                message="Test content"
            )
            self.batcher.add_message(message, user_id=i)
        
        # Flush all batches
        batch_count = self.batcher.flush_all_batches()
        
        self.assertGreaterEqual(batch_count, 1)
        self.assertTrue(self.mock_router.route_user_message.called)


class TestNotificationThrottler(unittest.TestCase):
    """Test notification throttling functionality"""
    
    def setUp(self):
        self.config = ThrottleConfiguration(
            max_messages_per_second=5,
            burst_capacity=10,
            user_rate_limit=2
        )
        self.throttler = NotificationThrottler(self.config)
    
    def test_normal_rate_limiting(self):
        """Test normal rate limiting behavior"""
        message = NotificationMessage(
            id="rate_test",
            type=NotificationType.INFO,
            title="Rate Test",
            message="Test content"
        )
        
        # Should allow first few messages
        for i in range(2):
            allowed = self.throttler.should_allow_message(message, user_id=1)
            self.assertTrue(allowed)
        
        # Should throttle after user limit
        allowed = self.throttler.should_allow_message(message, user_id=1)
        self.assertFalse(allowed)
    
    def test_priority_multipliers(self):
        """Test priority-based rate limiting"""
        high_priority_msg = NotificationMessage(
            id="high_priority",
            type=NotificationType.ERROR,
            title="High Priority",
            message="Test content",
            priority=NotificationPriority.HIGH
        )
        
        low_priority_msg = NotificationMessage(
            id="low_priority",
            type=NotificationType.INFO,
            title="Low Priority",
            message="Test content",
            priority=NotificationPriority.LOW
        )
        
        # Exhaust normal rate limit
        for i in range(2):
            self.throttler.should_allow_message(low_priority_msg, user_id=1)
        
        # High priority should still be allowed due to multiplier
        allowed = self.throttler.should_allow_message(high_priority_msg, user_id=1)
        self.assertTrue(allowed)
    
    def test_throttle_stats(self):
        """Test throttling statistics"""
        message = NotificationMessage(
            id="stats_test",
            type=NotificationType.INFO,
            title="Stats Test",
            message="Test content"
        )
        
        # Generate some throttling
        for i in range(5):
            self.throttler.should_allow_message(message, user_id=1)
        
        stats = self.throttler.get_throttle_stats()
        
        self.assertIn('current_global_rate', stats)
        self.assertIn('burst_tokens_available', stats)
        self.assertIn('stats', stats)


class TestMemoryManager(unittest.TestCase):
    """Test memory management functionality"""
    
    def setUp(self):
        self.config = MemoryConfiguration(
            max_memory_mb=100,
            gc_threshold=0.8,
            object_pooling=True
        )
        self.memory_manager = MemoryManager(self.config)
    
    def test_object_pooling(self):
        """Test object pooling functionality"""
        # Create factory function that returns an object that can have weak references
        class TestObject:
            def __init__(self):
                self.data = 'test'
                self.created = time.time()
            
            def reset(self):
                self.data = 'test'
        
        def create_test_object():
            return TestObject()
        
        # Get object from pool (should create new)
        obj1 = self.memory_manager.get_pooled_object('test_type', create_test_object)
        self.assertIsNotNone(obj1)
        
        # Return to pool
        self.memory_manager.return_to_pool('test_type', obj1)
        
        # Get object again (should reuse)
        obj2 = self.memory_manager.get_pooled_object('test_type', create_test_object)
        self.assertEqual(obj1, obj2)
    
    def test_memory_usage_check(self):
        """Test memory usage monitoring"""
        memory_info = self.memory_manager.check_memory_usage()
        
        self.assertIn('current_mb', memory_info)
        self.assertIn('max_mb', memory_info)
        self.assertIn('usage_percent', memory_info)
        self.assertIn('gc_threshold_reached', memory_info)
    
    def test_memory_cleanup(self):
        """Test memory cleanup functionality"""
        cleanup_stats = self.memory_manager.cleanup_memory()
        
        self.assertIn('objects_collected', cleanup_stats)
        self.assertIn('pools_cleared', cleanup_stats)
        self.assertIsInstance(cleanup_stats['objects_collected'], int)


class TestConnectionPool(unittest.TestCase):
    """Test WebSocket connection pool functionality"""
    
    def setUp(self):
        self.config = ConnectionPoolConfig(
            max_connections=10,
            max_connections_per_user=3,
            idle_timeout_seconds=5
        )
        self.resource_limits = ResourceLimits(
            max_total_memory_mb=100.0,
            max_total_cpu_percent=50.0
        )
        self.pool = ConnectionPool(self.config, self.resource_limits)
    
    def test_add_connection(self):
        """Test adding connections to pool"""
        success = self.pool.add_connection("session_1", user_id=1, namespace="/", priority=ConnectionPriority.NORMAL)
        self.assertTrue(success)
        
        # Check connection exists
        metrics = self.pool.get_connection_metrics("session_1")
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.user_id, 1)
        self.assertEqual(metrics.namespace, "/")
    
    def test_connection_limits(self):
        """Test connection limit enforcement"""
        # Add connections up to user limit
        for i in range(3):
            success = self.pool.add_connection(f"session_{i}", user_id=1, namespace="/")
            self.assertTrue(success)
        
        # Should reject additional connection for same user
        success = self.pool.add_connection("session_overflow", user_id=1, namespace="/")
        self.assertFalse(success)
    
    def test_remove_connection(self):
        """Test removing connections from pool"""
        self.pool.add_connection("session_remove", user_id=1, namespace="/")
        
        success = self.pool.remove_connection("session_remove")
        self.assertTrue(success)
        
        # Should not exist anymore
        metrics = self.pool.get_connection_metrics("session_remove")
        self.assertIsNone(metrics)
    
    def test_connection_activity_tracking(self):
        """Test connection activity tracking"""
        self.pool.add_connection("session_activity", user_id=1, namespace="/")
        
        # Update activity
        self.pool.update_connection_activity("session_activity", message_size=100, is_outbound=True)
        
        metrics = self.pool.get_connection_metrics("session_activity")
        self.assertEqual(metrics.messages_sent, 1)
        self.assertEqual(metrics.bytes_sent, 100)
    
    def test_message_queuing(self):
        """Test message queuing for connections"""
        self.pool.add_connection("session_queue", user_id=1, namespace="/")
        
        # Queue messages
        for i in range(3):
            message = {"type": "test", "data": f"message_{i}"}
            success = self.pool.queue_message("session_queue", message)
            self.assertTrue(success)
        
        # Get queued messages
        messages = self.pool.get_queued_messages("session_queue", max_messages=2)
        self.assertEqual(len(messages), 2)
    
    def test_pool_statistics(self):
        """Test connection pool statistics"""
        # Add some connections
        for i in range(3):
            self.pool.add_connection(f"session_stats_{i}", user_id=i, namespace="/")
        
        stats = self.pool.get_pool_stats()
        
        self.assertEqual(stats['total_connections'], 3)
        self.assertIn('utilization_percent', stats)
        self.assertIn('state_distribution', stats)
        self.assertIn('resource_usage', stats)


class TestDatabaseOptimizer(unittest.TestCase):
    """Test database optimization functionality"""
    
    def setUp(self):
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        
        # Properly mock the context manager
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=self.mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = context_manager
        
        self.config = DatabaseOptimizationConfig(
            enable_query_batching=True,
            enable_query_caching=True,
            max_batch_size=5,
            query_cache_size=100
        )
        self.optimizer = NotificationDatabaseOptimizer(self.mock_db_manager, self.config)
    
    def test_query_cache(self):
        """Test query result caching"""
        cache = QueryCache(max_size=10, ttl_seconds=60)
        
        # Cache miss
        result = cache.get("test_query")
        self.assertIsNone(result)
        
        # Cache put and hit
        test_data = {"result": "test"}
        cache.put("test_query", test_data)
        
        result = cache.get("test_query")
        self.assertEqual(result, test_data)
        
        # Check stats
        stats = cache.get_stats()
        self.assertEqual(stats['stats']['hits'], 1)
        self.assertEqual(stats['stats']['misses'], 1)
    
    def test_batch_processor(self):
        """Test batch operation processing"""
        batch_processor = BatchProcessor(self.mock_db_manager, self.config)
        
        # Add operations to batch
        for i in range(3):
            data = {
                'id': f'test_{i}',
                'user_id': 1,
                'title': f'Test {i}',
                'message': 'Test content'
            }
            batch_processor.add_operation(QueryType.INSERT, data)
        
        # Check batch stats
        stats = batch_processor.get_batch_stats()
        self.assertEqual(stats['stats']['operations_batched'], 3)
    
    def test_performance_monitor(self):
        """Test query performance monitoring"""
        monitor = QueryPerformanceMonitor(self.config)
        
        # Record some queries
        for i in range(5):
            monitor.record_query(
                QueryType.SELECT,
                execution_time_ms=100 + i * 10,
                rows_affected=1,
                query_hash=f"query_{i}"
            )
        
        # Get performance report
        report = monitor.get_performance_report()
        
        self.assertIn('overall_stats', report)
        self.assertIn('recent_performance', report)
        self.assertEqual(report['overall_stats']['total_queries'], 5)
    
    @patch('notification_database_optimizer.NotificationStorage')
    def test_optimize_notification_storage(self, mock_notification_storage):
        """Test optimized notification storage"""
        notification_data = {
            'id': 'test_notification',
            'user_id': 1,
            'title': 'Test Notification',
            'message': 'Test content',
            'type': NotificationType.INFO,
            'priority': NotificationPriority.NORMAL,
            'category': NotificationCategory.SYSTEM
        }
        
        success = self.optimizer.optimize_notification_storage(notification_data)
        self.assertTrue(success)
    
    def test_optimization_report(self):
        """Test optimization report generation"""
        report = self.optimizer.get_optimization_report()
        
        self.assertIn('timestamp', report)
        self.assertIn('optimization_stats', report)
        self.assertIn('configuration', report)


class TestNotificationPerformanceOptimizer(unittest.TestCase):
    """Test main performance optimizer integration"""
    
    def setUp(self):
        # Create mock dependencies
        self.mock_notification_manager = Mock()
        self.mock_message_router = Mock(spec=NotificationMessageRouter)
        self.mock_persistence_manager = Mock(spec=NotificationPersistenceManager)
        
        # Mock namespace manager for message router
        self.mock_namespace_manager = Mock()
        self.mock_message_router.namespace_manager = self.mock_namespace_manager
        self.mock_namespace_manager._connections = {}
        self.mock_namespace_manager._user_connections = {}
        
        self.optimizer = NotificationPerformanceOptimizer(
            self.mock_notification_manager,
            self.mock_message_router,
            self.mock_persistence_manager,
            OptimizationLevel.BALANCED
        )
    
    def test_optimize_message_delivery(self):
        """Test optimized message delivery"""
        message = NotificationMessage(
            id="test_optimize",
            type=NotificationType.INFO,
            title="Optimization Test",
            message="Test content"
        )
        
        # Mock throttler to allow message
        self.optimizer.throttler.should_allow_message = Mock(return_value=True)
        
        success = self.optimizer.optimize_message_delivery(message, user_id=1)
        self.assertTrue(success)
    
    def test_performance_metrics(self):
        """Test performance metrics collection"""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
            mock_process.return_value.cpu_percent.return_value = 25.0
            
            metrics = self.optimizer.get_performance_metrics()
            
            self.assertIsNotNone(metrics)
            self.assertEqual(metrics.memory_usage_mb, 100.0)
            self.assertEqual(metrics.cpu_usage_percent, 25.0)
    
    def test_optimization_report(self):
        """Test optimization report generation"""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 100 * 1024 * 1024
            mock_process.return_value.cpu_percent.return_value = 25.0
            
            report = self.optimizer.get_optimization_report()
            
            self.assertIn('optimization_level', report)
            self.assertIn('current_metrics', report)
            self.assertIn('optimization_stats', report)
            self.assertIn('component_stats', report)
            self.assertIn('recommendations', report)
    
    def test_optimization_level_adjustment(self):
        """Test optimization level adjustment"""
        success = self.optimizer.adjust_optimization_level(OptimizationLevel.AGGRESSIVE)
        self.assertTrue(success)
        self.assertEqual(self.optimizer.optimization_level, OptimizationLevel.AGGRESSIVE)
    
    def test_flush_optimizations(self):
        """Test flushing all optimizations"""
        results = self.optimizer.flush_all_optimizations()
        
        self.assertIn('batches_flushed', results)
        self.assertIn('cache_entries_cleared', results)
        self.assertIn('memory_cleaned', results)


class TestWebSocketConnectionOptimizer(unittest.TestCase):
    """Test WebSocket connection optimizer integration"""
    
    def setUp(self):
        self.mock_namespace_manager = Mock()
        self.config = ConnectionPoolConfig(max_connections=10)
        self.resource_limits = ResourceLimits()
        
        self.optimizer = WebSocketConnectionOptimizer(
            self.mock_namespace_manager,
            self.config,
            self.resource_limits
        )
    
    def test_optimize_connection_management(self):
        """Test connection management optimization"""
        # Add some test connections
        self.optimizer.connection_pool.add_connection("test_1", user_id=1, namespace="/")
        self.optimizer.connection_pool.add_connection("test_2", user_id=2, namespace="/")
        
        results = self.optimizer.optimize_connection_management()
        
        self.assertIn('optimization_results', results)
        self.assertIn('health_report', results)
        self.assertIn('pool_statistics', results)
        self.assertIn('recommendations', results)
    
    def test_performance_report(self):
        """Test connection performance report"""
        report = self.optimizer.get_connection_performance_report()
        
        self.assertIn('timestamp', report)
        self.assertIn('pool_statistics', report)
        self.assertIn('health_report', report)
        self.assertIn('configuration', report)
        self.assertIn('resource_limits', report)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
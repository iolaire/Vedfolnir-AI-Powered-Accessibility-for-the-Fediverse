# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Optimization Tests

Comprehensive tests for caching, query optimization, and background cleanup features.
"""

import unittest
import redis
import json
import time
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole, CaptionGenerationTask, TaskStatus, JobPriority, JobAuditLog
from performance_cache_manager import PerformanceCacheManager, CacheConfig, CacheKeyGenerator
from database_query_optimizer import DatabaseQueryOptimizer
from app.services.task.core.background_cleanup_manager import BackgroundCleanupManager, CleanupConfig
from app.services.admin.enhanced.enhanced_admin_management_service import EnhancedAdminManagementService
from app.services.task.core.task_queue_manager import TaskQueueManager

class TestPerformanceCacheManager(unittest.TestCase):
    """Test performance cache manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Mock Redis client for testing
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_redis.ping.return_value = True
        self.mock_redis.setex.return_value = True
        self.mock_redis.get.return_value = None
        self.mock_redis.delete.return_value = 1
        self.mock_redis.keys.return_value = []
        self.mock_redis.info.return_value = {
            'used_memory_human': '1.5M',
            'keyspace_hits': 100,
            'keyspace_misses': 20,
            'connected_clients': 5
        }
        
        self.cache_config = CacheConfig(
            admin_dashboard_ttl=300,
            job_status_ttl=60,
            user_permissions_ttl=1800,
            system_metrics_ttl=120
        )
        
        self.cache_manager = PerformanceCacheManager(
            self.mock_redis, 
            self.db_manager, 
            self.cache_config
        )
    
    def test_cache_key_generation(self):
        """Test cache key generation for different data types"""
        # Test admin dashboard key
        admin_key = CacheKeyGenerator.admin_dashboard(123)
        self.assertEqual(admin_key, "vedfolnir:cache:admin_dashboard:123")
        
        # Test job status key
        job_key = CacheKeyGenerator.job_status("task-123")
        self.assertEqual(job_key, "vedfolnir:cache:job_status:task-123")
        
        # Test user permissions key
        user_key = CacheKeyGenerator.user_permissions(456)
        self.assertEqual(user_key, "vedfolnir:cache:user_permissions:456")
        
        # Test system metrics key
        metrics_key = CacheKeyGenerator.system_metrics()
        self.assertEqual(metrics_key, "vedfolnir:cache:system_metrics")
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        test_data = {'key': 'value', 'number': 123}
        cache_key = 'test_key'
        
        # Mock successful set
        self.mock_redis.setex.return_value = True
        
        # Test set operation
        result = self.cache_manager.set_cache(cache_key, test_data, ttl=300)
        self.assertTrue(result)
        
        # Verify setex was called with correct parameters
        self.mock_redis.setex.assert_called_once()
        call_args = self.mock_redis.setex.call_args
        self.assertEqual(call_args[0][0], cache_key)  # key
        self.assertEqual(call_args[0][1], 300)  # ttl
        
        # Mock successful get
        cache_entry = {
            'data': test_data,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'ttl': 300
        }
        self.mock_redis.get.return_value = json.dumps(cache_entry)
        
        # Test get operation
        retrieved_data = self.cache_manager.get_cache(cache_key)
        self.assertEqual(retrieved_data, test_data)
    
    def test_admin_dashboard_caching(self):
        """Test admin dashboard data caching"""
        admin_user_id = 123
        dashboard_data = {
            'total_users': 10,
            'active_tasks': 5,
            'system_health': 95.5
        }
        
        # Test caching dashboard data
        result = self.cache_manager.cache_admin_dashboard_data(admin_user_id, dashboard_data)
        self.assertTrue(result)
        
        # Mock cached data retrieval
        cache_entry = {
            'data': dashboard_data,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'ttl': self.cache_config.admin_dashboard_ttl
        }
        self.mock_redis.get.return_value = json.dumps(cache_entry)
        
        # Test retrieving dashboard data
        retrieved_data = self.cache_manager.get_admin_dashboard_data(admin_user_id)
        self.assertEqual(retrieved_data, dashboard_data)
    
    def test_job_status_caching(self):
        """Test job status caching"""
        task_id = "task-123"
        status_data = {
            'status': 'running',
            'progress': 75,
            'current_step': 'processing_images'
        }
        
        # Test caching job status
        result = self.cache_manager.cache_job_status(task_id, status_data)
        self.assertTrue(result)
        
        # Mock cached data retrieval
        cache_entry = {
            'data': status_data,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'ttl': self.cache_config.job_status_ttl
        }
        self.mock_redis.get.return_value = json.dumps(cache_entry)
        
        # Test retrieving job status
        retrieved_data = self.cache_manager.get_job_status(task_id)
        self.assertEqual(retrieved_data, status_data)
    
    def test_user_permissions_caching(self):
        """Test user permissions caching"""
        user_id = 456
        permissions_data = {
            'user_id': user_id,
            'role': 'admin',
            'permissions': ['read', 'write', 'admin']
        }
        
        # Test caching user permissions
        result = self.cache_manager.cache_user_permissions(user_id, permissions_data)
        self.assertTrue(result)
        
        # Mock cached data retrieval
        cache_entry = {
            'data': permissions_data,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'ttl': self.cache_config.user_permissions_ttl
        }
        self.mock_redis.get.return_value = json.dumps(cache_entry)
        
        # Test retrieving user permissions
        retrieved_data = self.cache_manager.get_user_permissions(user_id)
        self.assertEqual(retrieved_data, permissions_data)
    
    def test_cache_invalidation(self):
        """Test cache invalidation patterns"""
        user_id = 123
        
        # Mock keys method to return user-related keys
        user_keys = [
            f"vedfolnir:cache:user_permissions:{user_id}",
            f"vedfolnir:cache:user_jobs:{user_id}",
            f"vedfolnir:cache:admin_dashboard:{user_id}"
        ]
        self.mock_redis.keys.return_value = user_keys
        self.mock_redis.delete.return_value = len(user_keys)
        
        # Test user cache invalidation
        invalidated_count = self.cache_manager.invalidate_user_caches(user_id)
        self.assertEqual(invalidated_count, len(user_keys))
    
    def test_cache_statistics(self):
        """Test cache statistics collection"""
        # Mock Redis info response
        self.mock_redis.info.return_value = {
            'used_memory_human': '2.5M',
            'keyspace_hits': 150,
            'keyspace_misses': 30,
            'connected_clients': 8
        }
        
        # Mock cache keys
        cache_keys = [
            'vedfolnir:cache:admin_dashboard:123',
            'vedfolnir:cache:job_status:task-456',
            'vedfolnir:cache:system_metrics'
        ]
        self.mock_redis.keys.return_value = cache_keys
        
        # Get cache statistics
        stats = self.cache_manager.get_cache_stats()
        
        # Verify statistics
        self.assertEqual(stats['total_cache_keys'], len(cache_keys))
        self.assertEqual(stats['redis_memory_used'], '2.5M')
        self.assertEqual(stats['redis_keyspace_hits'], 150)
        self.assertEqual(stats['redis_keyspace_misses'], 30)
        self.assertEqual(stats['cache_hit_rate'], 83.33)  # 150/(150+30)*100

class TestDatabaseQueryOptimizer(unittest.TestCase):
    """Test database query optimizer functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Mock cache manager
        self.mock_cache_manager = Mock(spec=PerformanceCacheManager)
        self.mock_cache_manager.get_admin_dashboard_data.return_value = None
        self.mock_cache_manager.cache_admin_dashboard_data.return_value = True
        
        self.query_optimizer = DatabaseQueryOptimizer(
            self.db_manager, 
            self.mock_cache_manager
        )
    
    @patch('database_query_optimizer.datetime')
    def test_query_performance_tracking(self, mock_datetime):
        """Test query performance tracking"""
        # Mock datetime for consistent testing
        mock_now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        # Track a query
        self.query_optimizer._track_query_performance(
            'test_query', 150.5, 10, cache_hit=False
        )
        
        # Verify metric was recorded
        self.assertEqual(len(self.query_optimizer._query_metrics), 1)
        metric = self.query_optimizer._query_metrics[0]
        self.assertEqual(metric.query_name, 'test_query')
        self.assertEqual(metric.execution_time_ms, 150.5)
        self.assertEqual(metric.rows_returned, 10)
        self.assertFalse(metric.cache_hit)
    
    def test_query_performance_stats(self):
        """Test query performance statistics calculation"""
        # Add some test metrics
        self.query_optimizer._query_metrics = [
            Mock(query_name='query1', execution_time_ms=100, rows_returned=5, cache_hit=False),
            Mock(query_name='query1', execution_time_ms=200, rows_returned=10, cache_hit=True),
            Mock(query_name='query2', execution_time_ms=50, rows_returned=3, cache_hit=False),
        ]
        
        # Get performance stats
        stats = self.query_optimizer.get_query_performance_stats()
        
        # Verify statistics
        self.assertEqual(stats['total_queries'], 3)
        self.assertEqual(stats['cache_hit_rate'], 33.33)  # 1/3 * 100
        self.assertEqual(stats['avg_execution_time_ms'], 116.67)  # (100+200+50)/3
        
        # Verify query breakdown
        self.assertIn('query1', stats['query_breakdown'])
        self.assertIn('query2', stats['query_breakdown'])
        
        query1_stats = stats['query_breakdown']['query1']
        self.assertEqual(query1_stats['count'], 2)
        self.assertEqual(query1_stats['cache_hit_rate'], 50.0)  # 1/2 * 100

class TestBackgroundCleanupManager(unittest.TestCase):
    """Test background cleanup manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Mock Redis client
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_redis.keys.return_value = []
        self.mock_redis.delete.return_value = 0
        
        self.cleanup_config = CleanupConfig(
            audit_log_retention_days=30,
            metrics_retention_days=7,
            cache_cleanup_interval_minutes=5,
            database_cleanup_interval_hours=1,
            cleanup_enabled=True
        )
        
        self.cleanup_manager = BackgroundCleanupManager(
            self.db_manager,
            self.mock_redis,
            config=self.cleanup_config
        )
    
    def test_cleanup_config(self):
        """Test cleanup configuration"""
        self.assertEqual(self.cleanup_config.audit_log_retention_days, 30)
        self.assertEqual(self.cleanup_config.metrics_retention_days, 7)
        self.assertTrue(self.cleanup_config.cleanup_enabled)
    
    def test_manual_cleanup_execution(self):
        """Test manual cleanup execution"""
        # Mock cleanup function
        with patch.object(self.cleanup_manager, '_cleanup_old_audit_logs', return_value=5):
            result = self.cleanup_manager.run_manual_cleanup('audit_logs')
            
            self.assertTrue(result['success'])
            self.assertEqual(result['cleanup_type'], 'audit_logs')
            self.assertEqual(result['items_cleaned'], 5)
            self.assertIn('execution_time_seconds', result)
            self.assertIn('timestamp', result)
    
    def test_manual_cleanup_invalid_type(self):
        """Test manual cleanup with invalid type"""
        result = self.cleanup_manager.run_manual_cleanup('invalid_type')
        
        self.assertFalse(result['success'])
        self.assertIn('Unknown cleanup type', result['error'])
        self.assertIn('available_types', result)
    
    def test_cleanup_stats_recording(self):
        """Test cleanup statistics recording"""
        # Run a manual cleanup to generate stats
        with patch.object(self.cleanup_manager, '_cleanup_old_audit_logs', return_value=3):
            self.cleanup_manager.run_manual_cleanup('audit_logs')
        
        # Get cleanup stats
        stats = self.cleanup_manager.get_cleanup_stats(hours=1)
        
        # Verify stats were recorded
        self.assertIn('summary', stats)
        self.assertEqual(stats['summary']['total_operations'], 1)
        self.assertEqual(stats['summary']['successful_operations'], 1)
        self.assertEqual(stats['summary']['total_items_cleaned'], 3)
    
    def test_background_cleanup_thread_management(self):
        """Test background cleanup thread management"""
        # Start background cleanup
        self.cleanup_manager.start_background_cleanup()
        
        # Verify threads were started
        self.assertGreater(len(self.cleanup_manager._cleanup_threads), 0)
        
        # Stop background cleanup
        self.cleanup_manager.stop_background_cleanup()
        
        # Verify threads were stopped
        self.assertEqual(len(self.cleanup_manager._cleanup_threads), 0)

class TestEnhancedAdminManagementService(unittest.TestCase):
    """Test enhanced admin management service with caching"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Mock dependencies
        self.mock_task_queue_manager = Mock(spec=TaskQueueManager)
        self.mock_cache_manager = Mock(spec=PerformanceCacheManager)
        self.mock_cleanup_manager = Mock(spec=BackgroundCleanupManager)
        
        self.enhanced_service = EnhancedAdminManagementService(
            self.db_manager,
            self.mock_task_queue_manager,
            self.mock_cache_manager,
            self.mock_cleanup_manager
        )
    
    def test_cached_system_overview_cache_hit(self):
        """Test system overview with cache hit"""
        admin_user_id = 123
        cached_data = {
            'user_statistics': {'total_users': 10, 'active_users': 8},
            'task_statistics': {'total_tasks': 50, 'active_tasks': 5},
            'performance_metrics': {'success_rate': 95.0},
            'recent_errors': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Mock cache hit
        self.mock_cache_manager.get_admin_dashboard_data.return_value = cached_data
        
        # Get system overview
        overview = self.enhanced_service.get_system_overview_cached(admin_user_id)
        
        # Verify cache hit
        self.assertTrue(overview.cache_hit)
        self.assertEqual(overview.total_users, 10)
        self.assertEqual(overview.active_users, 8)
        self.assertIsNotNone(overview.cache_timestamp)
    
    def test_cached_system_overview_cache_miss(self):
        """Test system overview with cache miss"""
        admin_user_id = 123
        
        # Mock cache miss
        self.mock_cache_manager.get_admin_dashboard_data.return_value = None
        
        # Mock query optimizer
        with patch.object(self.enhanced_service.query_optimizer, 'get_admin_dashboard_data_optimized') as mock_optimizer:
            mock_optimizer.return_value = {
                'user_statistics': {'total_users': 15, 'active_users': 12},
                'task_statistics': {
                    'total_tasks': 75, 'active_tasks': 8, 'queued_tasks': 3,
                    'running_tasks': 5, 'completed_tasks': 60, 'failed_tasks': 7,
                    'cancelled_tasks': 0
                },
                'performance_metrics': {'success_rate': 88.0},
                'recent_errors': [],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Mock resource usage
            with patch.object(self.enhanced_service, '_get_resource_usage', return_value={}):
                overview = self.enhanced_service.get_system_overview_cached(admin_user_id)
        
        # Verify cache miss
        self.assertFalse(overview.cache_hit)
        self.assertEqual(overview.total_users, 15)
        self.assertEqual(overview.active_users, 12)
        self.assertGreater(overview.query_time_ms, 0)
    
    def test_cache_invalidation_after_job_cancellation(self):
        """Test cache invalidation after job cancellation"""
        admin_user_id = 123
        task_id = "task-456"
        reason = "Test cancellation"
        
        # Mock successful cancellation
        with patch.object(self.enhanced_service, 'cancel_job_as_admin', return_value=True):
            result = self.enhanced_service.cancel_job_as_admin_with_cache_invalidation(
                admin_user_id, task_id, reason
            )
        
        # Verify cancellation succeeded
        self.assertTrue(result)
        
        # Verify cache invalidation was called
        self.mock_cache_manager.invalidate_job_caches.assert_called_once_with(task_id)
        self.mock_cache_manager.delete_cache.assert_called()
    
    def test_user_permissions_caching(self):
        """Test user permissions caching"""
        user_id = 456
        
        # Mock cache miss
        self.mock_cache_manager.get_user_permissions.return_value = None
        
        # Mock database user
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.username = 'testuser'
        mock_user.email = 'test@example.com'
        mock_user.role = UserRole.ADMIN
        mock_user.is_active = True
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.last_login = None
        
        # Mock database session
        with patch.object(self.db_manager, 'get_session') as mock_session_context:
            mock_session = Mock()
            mock_session_context.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
            
            # Get user permissions
            permissions = self.enhanced_service.get_cached_user_permissions(user_id)
        
        # Verify permissions data
        self.assertEqual(permissions['user_id'], user_id)
        self.assertEqual(permissions['username'], 'testuser')
        self.assertEqual(permissions['role'], 'admin')
        self.assertTrue(permissions['is_admin'])
        self.assertTrue(permissions['can_manage_users'])
        
        # Verify caching was called
        self.mock_cache_manager.cache_user_permissions.assert_called_once()
    
    def test_performance_metrics_collection(self):
        """Test performance metrics collection"""
        # Mock cache stats
        self.mock_cache_manager.get_cache_stats.return_value = {
            'cache_hit_rate': 75.5,
            'total_cache_keys': 150,
            'redis_memory_used': '2.5M'
        }
        
        # Mock query stats
        with patch.object(self.enhanced_service.query_optimizer, 'get_query_performance_stats') as mock_query_stats:
            mock_query_stats.return_value = {
                'avg_execution_time_ms': 125.0,
                'total_queries': 500
            }
            
            # Mock cleanup stats
            self.mock_cleanup_manager.get_cleanup_stats.return_value = {
                'summary': {'total_operations': 10}
            }
            
            # Get performance metrics
            metrics = self.enhanced_service.get_system_performance_metrics()
        
        # Verify metrics
        self.assertEqual(metrics.cache_hit_rate, 75.5)
        self.assertEqual(metrics.avg_query_time_ms, 125.0)
        self.assertEqual(metrics.total_cached_operations, 150)
        self.assertEqual(metrics.cache_memory_usage_mb, 2.5)
        self.assertIsInstance(metrics.background_cleanup_stats, dict)
    
    def test_manual_cleanup_execution(self):
        """Test manual cleanup execution through admin service"""
        admin_user_id = 123
        cleanup_type = 'audit_logs'
        
        # Mock admin authorization
        with patch.object(self.enhanced_service, '_verify_admin_authorization'):
            with patch.object(self.enhanced_service, '_log_admin_action'):
                with patch.object(self.db_manager, 'get_session') as mock_session_context:
                    mock_session = Mock()
                    mock_session_context.return_value.__enter__.return_value = mock_session
                    
                    # Mock cleanup result
                    self.mock_cleanup_manager.run_manual_cleanup.return_value = {
                        'success': True,
                        'cleanup_type': cleanup_type,
                        'items_cleaned': 25,
                        'execution_time_seconds': 1.5
                    }
                    
                    # Run manual cleanup
                    result = self.enhanced_service.run_manual_cleanup(cleanup_type, admin_user_id)
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['cleanup_type'], cleanup_type)
        self.assertEqual(result['items_cleaned'], 25)
        self.assertEqual(result['admin_user_id'], admin_user_id)
        self.assertIn('requested_at', result)

class TestPerformanceIntegration(unittest.TestCase):
    """Integration tests for performance optimization features"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Use real Redis client for integration tests (if available)
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
            self.redis_client.ping()
            self.redis_available = True
        except:
            self.redis_client = Mock(spec=redis.Redis)
            self.redis_available = False
            self.skipTest("Redis not available for integration tests")
    
    def tearDown(self):
        """Clean up after integration tests"""
        if self.redis_available:
            # Clean up test data
            test_keys = self.redis_client.keys("vedfolnir:cache:*")
            if test_keys:
                self.redis_client.delete(*test_keys)
    
    def test_end_to_end_caching_workflow(self):
        """Test complete caching workflow"""
        if not self.redis_available:
            self.skipTest("Redis not available")
        
        # Create cache manager
        cache_manager = PerformanceCacheManager(self.redis_client, self.db_manager)
        
        # Test data
        admin_user_id = 999
        dashboard_data = {
            'total_users': 100,
            'active_tasks': 25,
            'system_health': 98.5,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Cache the data
        success = cache_manager.cache_admin_dashboard_data(admin_user_id, dashboard_data)
        self.assertTrue(success)
        
        # Retrieve the data
        retrieved_data = cache_manager.get_admin_dashboard_data(admin_user_id)
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data['total_users'], 100)
        self.assertEqual(retrieved_data['active_tasks'], 25)
        
        # Test cache invalidation
        invalidated = cache_manager.invalidate_user_caches(admin_user_id)
        self.assertGreater(invalidated, 0)
        
        # Verify data is gone
        retrieved_after_invalidation = cache_manager.get_admin_dashboard_data(admin_user_id)
        self.assertIsNone(retrieved_after_invalidation)
    
    def test_concurrent_cache_operations(self):
        """Test concurrent cache operations"""
        if not self.redis_available:
            self.skipTest("Redis not available")
        
        cache_manager = PerformanceCacheManager(self.redis_client, self.db_manager)
        
        def cache_worker(worker_id):
            """Worker function for concurrent testing"""
            for i in range(10):
                key = f"test_key_{worker_id}_{i}"
                data = {'worker': worker_id, 'iteration': i}
                cache_manager.set_cache(key, data, ttl=60)
                
                # Retrieve immediately
                retrieved = cache_manager.get_cache(key)
                self.assertEqual(retrieved['worker'], worker_id)
                self.assertEqual(retrieved['iteration'], i)
        
        # Start multiple worker threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=cache_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all data was cached correctly
        test_keys = self.redis_client.keys("vedfolnir:cache:test_key_*")
        self.assertEqual(len(test_keys), 50)  # 5 workers * 10 iterations

if __name__ == '__main__':
    unittest.main()
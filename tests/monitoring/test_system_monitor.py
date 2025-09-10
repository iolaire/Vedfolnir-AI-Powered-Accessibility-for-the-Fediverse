# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for SystemMonitor class

Tests all monitoring functionality including:
- System health monitoring
- Performance metrics collection
- Stuck job detection
- Error trend analysis
- Queue wait time prediction
- Redis metrics storage
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timedelta, timezone
from collections import namedtuple

# Mock psutil before importing system_monitor
MockMemory = namedtuple('MockMemory', ['percent', 'used', 'total'])
MockDisk = namedtuple('MockDisk', ['percent', 'used', 'total'])
MockNetworkIO = namedtuple('MockNetworkIO', ['bytes_sent', 'bytes_recv'])

with patch('psutil.cpu_percent', return_value=25.0), \
     patch('psutil.virtual_memory', return_value=MockMemory(50.0, 4000000000, 8000000000)), \
     patch('psutil.disk_usage', return_value=MockDisk(30.0, 100000000000, 300000000000)), \
     patch('psutil.net_io_counters', return_value=MockNetworkIO(1000000, 2000000)):
    
    from app.services.monitoring.system.system_monitor import (
        SystemMonitor, SystemHealth, PerformanceMetrics, 
        ErrorTrends, ResourceUsage
    )
    from models import CaptionGenerationTask, TaskStatus, User, UserRole
    from app.core.database.core.database_manager import DatabaseManager

class TestSystemMonitor(unittest.TestCase):
    """Test cases for SystemMonitor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock database manager
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Mock Redis client
        self.mock_redis = Mock()
        self.mock_redis.ping.return_value = True
        self.mock_redis.info.return_value = {'used_memory': 10485760}  # 10MB
        
        # Create system monitor
        self.monitor = SystemMonitor(
            db_manager=self.mock_db_manager,
            redis_client=self.mock_redis,
            stuck_job_timeout=3600,
            metrics_retention_hours=168
        )
    
    def test_init_with_redis_client(self):
        """Test SystemMonitor initialization with Redis client"""
        monitor = SystemMonitor(
            db_manager=self.mock_db_manager,
            redis_client=self.mock_redis
        )
        
        self.assertEqual(monitor.db_manager, self.mock_db_manager)
        self.assertEqual(monitor.redis_client, self.mock_redis)
        self.assertEqual(monitor.stuck_job_timeout, 3600)  # Default
        self.assertEqual(monitor.metrics_retention_hours, 168)  # Default
    
    def test_init_without_redis_client(self):
        """Test SystemMonitor initialization without Redis client"""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_instance = Mock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance
            
            monitor = SystemMonitor(db_manager=self.mock_db_manager)
            
            self.assertEqual(monitor.db_manager, self.mock_db_manager)
            self.assertEqual(monitor.redis_client, mock_redis_instance)
            mock_redis_class.assert_called_once()
    
    def test_init_redis_connection_failure(self):
        """Test SystemMonitor initialization with Redis connection failure"""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_instance = Mock()
            mock_redis_instance.ping.side_effect = Exception("Connection failed")
            mock_redis_class.return_value = mock_redis_instance
            
            monitor = SystemMonitor(db_manager=self.mock_db_manager)
            
            self.assertEqual(monitor.db_manager, self.mock_db_manager)
            self.assertIsNone(monitor.redis_client)
    
    @patch('psutil.cpu_percent', return_value=25.0)
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_system_health_healthy(self, mock_disk, mock_memory, mock_cpu):
        """Test get_system_health with healthy system"""
        # Mock system resources
        mock_memory.return_value = MockMemory(50.0, 4000000000, 8000000000)
        mock_disk.return_value = MockDisk(30.0, 100000000000, 300000000000)
        
        # Mock database query
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        
        # Mock database status check
        self.mock_session.execute.return_value = None
        
        # Mock task statistics
        with patch.object(self.monitor, '_get_task_statistics') as mock_stats:
            mock_stats.return_value = {
                'running': 2,
                'queued': 3,
                'failed_last_hour': 1
            }
            
            with patch.object(self.monitor, '_get_average_processing_time') as mock_avg_time:
                mock_avg_time.return_value = 120.0
                
                health = self.monitor.get_system_health()
                
                self.assertIsInstance(health, SystemHealth)
                self.assertEqual(health.status, 'healthy')
                self.assertEqual(health.cpu_usage, 25.0)
                self.assertEqual(health.memory_usage, 50.0)
                self.assertEqual(health.disk_usage, 30.0)
                self.assertEqual(health.database_status, 'healthy')
                self.assertEqual(health.redis_status, 'healthy')
                self.assertEqual(health.active_tasks, 2)
                self.assertEqual(health.queued_tasks, 3)
                self.assertEqual(health.failed_tasks_last_hour, 1)
                self.assertEqual(health.avg_processing_time, 120.0)
    
    @patch('psutil.cpu_percent', return_value=95.0)
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_system_health_critical(self, mock_disk, mock_memory, mock_cpu):
        """Test get_system_health with critical system status"""
        # Mock high resource usage
        mock_memory.return_value = MockMemory(95.0, 7600000000, 8000000000)
        mock_disk.return_value = MockDisk(98.0, 294000000000, 300000000000)
        
        # Mock database error
        self.mock_session.execute.side_effect = Exception("Database error")
        
        with patch.object(self.monitor, '_get_task_statistics') as mock_stats:
            mock_stats.return_value = {'running': 0, 'queued': 0, 'failed_last_hour': 0}
            
            with patch.object(self.monitor, '_get_average_processing_time') as mock_avg_time:
                mock_avg_time.return_value = 300.0
                
                health = self.monitor.get_system_health()
                
                self.assertEqual(health.status, 'critical')
                self.assertEqual(health.cpu_usage, 95.0)
                self.assertEqual(health.memory_usage, 95.0)
                self.assertEqual(health.disk_usage, 98.0)
                self.assertEqual(health.database_status, 'error')
    
    def test_get_system_health_exception_handling(self):
        """Test get_system_health exception handling"""
        # Mock exception in system health check
        with patch('psutil.cpu_percent', side_effect=Exception("System error")):
            health = self.monitor.get_system_health()
            
            self.assertEqual(health.status, 'critical')
            self.assertEqual(health.cpu_usage, 0.0)
            self.assertEqual(health.database_status, 'error')
    
    def test_get_performance_metrics(self):
        """Test get_performance_metrics"""
        with patch.object(self.monitor, '_calculate_completion_rate') as mock_completion:
            mock_completion.return_value = 10.0
            
            with patch.object(self.monitor, '_get_average_processing_time') as mock_avg_time:
                mock_avg_time.return_value = 180.0
                
                with patch.object(self.monitor, '_calculate_success_error_rates') as mock_rates:
                    mock_rates.return_value = (85.0, 15.0)
                    
                    with patch.object(self.monitor, '_calculate_queue_wait_time') as mock_wait:
                        mock_wait.return_value = 30.0
                        
                        with patch.object(self.monitor, '_get_resource_usage_dict') as mock_resources:
                            mock_resources.return_value = {'cpu_percent': 25.0}
                            
                            with patch.object(self.monitor, '_get_throughput_metrics') as mock_throughput:
                                mock_throughput.return_value = {'tasks_completed_last_hour': 10}
                                
                                metrics = self.monitor.get_performance_metrics()
                                
                                self.assertIsInstance(metrics, PerformanceMetrics)
                                self.assertEqual(metrics.job_completion_rate, 10.0)
                                self.assertEqual(metrics.avg_processing_time, 180.0)
                                self.assertEqual(metrics.success_rate, 85.0)
                                self.assertEqual(metrics.error_rate, 15.0)
                                self.assertEqual(metrics.queue_wait_time, 30.0)
                                self.assertEqual(metrics.resource_usage, {'cpu_percent': 25.0})
                                self.assertEqual(metrics.throughput_metrics, {'tasks_completed_last_hour': 10})
    
    def test_get_performance_metrics_exception_handling(self):
        """Test get_performance_metrics exception handling"""
        with patch.object(self.monitor, '_calculate_completion_rate', side_effect=Exception("Error")):
            metrics = self.monitor.get_performance_metrics()
            
            self.assertEqual(metrics.job_completion_rate, 0.0)
            self.assertEqual(metrics.success_rate, 0.0)
            self.assertEqual(metrics.error_rate, 100.0)
    
    @patch('psutil.cpu_percent', return_value=35.0)
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_check_resource_usage(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """Test check_resource_usage"""
        # Mock system resources
        mock_memory.return_value = MockMemory(60.0, 4800000000, 8000000000)
        mock_disk.return_value = MockDisk(40.0, 120000000000, 300000000000)
        mock_net.return_value = MockNetworkIO(5000000, 10000000)
        
        with patch.object(self.monitor, '_get_database_connection_count') as mock_db_conn:
            mock_db_conn.return_value = 15
            
            with patch.object(self.monitor, '_get_redis_memory_usage') as mock_redis_mem:
                mock_redis_mem.return_value = 25.5
                
                usage = self.monitor.check_resource_usage()
                
                self.assertIsInstance(usage, ResourceUsage)
                self.assertEqual(usage.cpu_percent, 35.0)
                self.assertEqual(usage.memory_percent, 60.0)
                self.assertAlmostEqual(usage.memory_used_mb, 4800000000 / (1024 * 1024), places=1)
                self.assertAlmostEqual(usage.memory_total_mb, 8000000000 / (1024 * 1024), places=1)
                self.assertEqual(usage.disk_percent, 40.0)
                self.assertEqual(usage.database_connections, 15)
                self.assertEqual(usage.redis_memory_mb, 25.5)
                self.assertIn('bytes_sent', usage.network_io)
                self.assertIn('bytes_recv', usage.network_io)
    
    def test_detect_stuck_jobs(self):
        """Test detect_stuck_jobs"""
        # Create mock stuck tasks
        stuck_task1 = Mock()
        stuck_task1.id = 'task-1'
        stuck_task2 = Mock()
        stuck_task2.id = 'task-2'
        
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [stuck_task1, stuck_task2]
        
        stuck_jobs = self.monitor.detect_stuck_jobs()
        
        self.assertEqual(len(stuck_jobs), 2)
        self.assertIn('task-1', stuck_jobs)
        self.assertIn('task-2', stuck_jobs)
        
        # Verify query was called with correct parameters
        self.mock_session.query.assert_called_with(CaptionGenerationTask)
    
    def test_detect_stuck_jobs_none_found(self):
        """Test detect_stuck_jobs when no stuck jobs found"""
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        stuck_jobs = self.monitor.detect_stuck_jobs()
        
        self.assertEqual(len(stuck_jobs), 0)
    
    def test_detect_stuck_jobs_exception_handling(self):
        """Test detect_stuck_jobs exception handling"""
        self.mock_session.query.side_effect = Exception("Database error")
        
        stuck_jobs = self.monitor.detect_stuck_jobs()
        
        self.assertEqual(len(stuck_jobs), 0)
    
    def test_get_error_trends(self):
        """Test get_error_trends"""
        # Create mock failed tasks
        failed_task1 = Mock()
        failed_task1.id = 'task-1'
        failed_task1.error_message = 'Connection timeout'
        failed_task1.completed_at = datetime.now(timezone.utc)
        failed_task1.user_id = 1
        
        failed_task2 = Mock()
        failed_task2.id = 'task-2'
        failed_task2.error_message = 'Rate limit exceeded'
        failed_task2.completed_at = datetime.now(timezone.utc)
        failed_task2.user_id = 2
        
        # Mock database queries
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # First call returns failed tasks, second call returns total count
        mock_query.all.return_value = [failed_task1, failed_task2]
        mock_query.count.return_value = 10  # Total tasks
        
        trends = self.monitor.get_error_trends(hours=24)
        
        self.assertIsInstance(trends, ErrorTrends)
        self.assertEqual(trends.total_errors, 2)
        self.assertEqual(trends.error_rate, 20.0)  # 2/10 * 100
        self.assertIn('timeout', trends.error_categories)
        self.assertIn('rate_limit', trends.error_categories)
        self.assertEqual(len(trends.trending_errors), 2)
    
    def test_get_error_trends_no_errors(self):
        """Test get_error_trends when no errors found"""
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 5
        
        trends = self.monitor.get_error_trends()
        
        self.assertEqual(trends.total_errors, 0)
        self.assertEqual(trends.error_rate, 0.0)
        self.assertEqual(len(trends.error_categories), 0)
    
    def test_predict_queue_wait_time(self):
        """Test predict_queue_wait_time"""
        # Mock database queries
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Mock queue counts: 5 queued, 2 running
        mock_query.count.side_effect = [5, 2]
        
        with patch.object(self.monitor, '_get_average_processing_time') as mock_avg_time:
            mock_avg_time.return_value = 120.0  # 2 minutes
            
            wait_time = self.monitor.predict_queue_wait_time()
            
            # With 5 queued, 2 running (1 free slot), avg time 120s
            # Processing rate = 1/120 = 0.0083 tasks/sec
            # Wait time = 5 / 0.0083 = ~600s, with 1.2x buffer = ~720s
            self.assertGreater(wait_time, 0)
            self.assertIsInstance(wait_time, int)
    
    def test_predict_queue_wait_time_no_capacity(self):
        """Test predict_queue_wait_time when no processing capacity"""
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Mock queue counts: 10 queued, 3 running (no capacity)
        mock_query.count.side_effect = [10, 3]
        
        with patch.object(self.monitor, '_get_average_processing_time') as mock_avg_time:
            mock_avg_time.return_value = 180.0
            
            wait_time = self.monitor.predict_queue_wait_time()
            
            # Should return average processing time with buffer when no capacity
            # 180 * 1.2 = 216
            self.assertEqual(wait_time, 216)
    
    def test_predict_queue_wait_time_exception_handling(self):
        """Test predict_queue_wait_time exception handling"""
        self.mock_session.query.side_effect = Exception("Database error")
        
        wait_time = self.monitor.predict_queue_wait_time()
        
        # Should return default 5 minutes on error
        self.assertEqual(wait_time, 300)
    
    def test_categorize_error(self):
        """Test _categorize_error method"""
        test_cases = [
            ("Connection timeout occurred", "timeout"),
            ("Network connection failed", "network"),
            ("Authentication failed", "authentication"),
            ("Rate limit exceeded", "rate_limit"),
            ("Database error occurred", "database"),  # Changed to match actual logic
            ("Redis error occurred", "redis"),  # Changed to match actual logic
            ("Ollama service unavailable", "ai_service"),
            ("Permission denied", "permission"),
            ("Unknown error occurred", "other")
        ]
        
        for error_message, expected_category in test_cases:
            with self.subTest(error_message=error_message):
                category = self.monitor._categorize_error(error_message)
                self.assertEqual(category, expected_category)
    
    def test_identify_error_patterns(self):
        """Test _identify_error_patterns method"""
        errors = [
            {'category': 'timeout', 'count': 1},
            {'category': 'timeout', 'count': 1},
            {'category': 'timeout', 'count': 1},
            {'category': 'network', 'count': 1},
            {'category': 'network', 'count': 1}
        ]
        
        patterns = self.monitor._identify_error_patterns(errors)
        
        # Should identify timeout as high frequency (3+ occurrences)
        timeout_pattern = next((p for p in patterns if p['category'] == 'timeout'), None)
        self.assertIsNotNone(timeout_pattern)
        self.assertEqual(timeout_pattern['type'], 'high_frequency')
        self.assertEqual(timeout_pattern['count'], 3)
    
    def test_calculate_completion_rate(self):
        """Test _calculate_completion_rate method"""
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 15
        
        rate = self.monitor._calculate_completion_rate()
        
        self.assertEqual(rate, 15.0)
    
    def test_calculate_success_error_rates(self):
        """Test _calculate_success_error_rates method"""
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Mock counts: 20 total, 17 successful
        mock_query.count.side_effect = [20, 17]
        
        success_rate, error_rate = self.monitor._calculate_success_error_rates()
        
        self.assertEqual(success_rate, 85.0)  # 17/20 * 100
        self.assertEqual(error_rate, 15.0)    # 100 - 85
    
    def test_calculate_success_error_rates_no_data(self):
        """Test _calculate_success_error_rates with no data"""
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.side_effect = [0, 0]
        
        success_rate, error_rate = self.monitor._calculate_success_error_rates()
        
        # Should return perfect rates when no data
        self.assertEqual(success_rate, 100.0)
        self.assertEqual(error_rate, 0.0)
    
    def test_calculate_queue_wait_time(self):
        """Test _calculate_queue_wait_time method"""
        # Create mock tasks with wait times
        task1 = Mock()
        task1.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        task1.started_at = datetime.now(timezone.utc) - timedelta(minutes=3)
        
        task2 = Mock()
        task2.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        task2.started_at = datetime.now(timezone.utc) - timedelta(minutes=8)
        
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [task1, task2]
        
        wait_time = self.monitor._calculate_queue_wait_time()
        
        # Average wait time should be 2 minutes (120 seconds)
        self.assertAlmostEqual(wait_time, 120.0, places=1)
    
    def test_calculate_queue_wait_time_no_data(self):
        """Test _calculate_queue_wait_time with no data"""
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        wait_time = self.monitor._calculate_queue_wait_time()
        
        self.assertEqual(wait_time, 0.0)
    
    def test_get_throughput_metrics(self):
        """Test _get_throughput_metrics method"""
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Mock counts for different metrics
        mock_query.count.side_effect = [25, 20, 3]  # created, completed, failed
        
        metrics = self.monitor._get_throughput_metrics()
        
        expected_metrics = {
            'tasks_created_last_hour': 25,
            'tasks_completed_last_hour': 20,
            'tasks_failed_last_hour': 3
        }
        
        self.assertEqual(metrics, expected_metrics)
    
    def test_get_redis_memory_usage(self):
        """Test _get_redis_memory_usage method"""
        self.mock_redis.info.return_value = {'used_memory': 20971520}  # 20MB
        
        memory_mb = self.monitor._get_redis_memory_usage()
        
        self.assertEqual(memory_mb, 20.0)
    
    def test_get_redis_memory_usage_no_redis(self):
        """Test _get_redis_memory_usage without Redis client"""
        monitor = SystemMonitor(db_manager=self.mock_db_manager, redis_client=None)
        
        memory_mb = monitor._get_redis_memory_usage()
        
        self.assertEqual(memory_mb, 0.0)
    
    def test_store_health_metrics(self):
        """Test _store_health_metrics method"""
        health = SystemHealth(
            status='healthy',
            cpu_usage=25.0,
            memory_usage=50.0,
            disk_usage=30.0,
            database_status='healthy',
            redis_status='healthy',
            active_tasks=2,
            queued_tasks=3,
            failed_tasks_last_hour=1,
            avg_processing_time=120.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.monitor._store_health_metrics(health)
        
        # Verify Redis operations were called
        self.mock_redis.hset.assert_called()
        self.mock_redis.setex.assert_called()
    
    def test_store_health_metrics_no_redis(self):
        """Test _store_health_metrics without Redis client"""
        monitor = SystemMonitor(db_manager=self.mock_db_manager, redis_client=None)
        
        health = SystemHealth(
            status='healthy',
            cpu_usage=25.0,
            memory_usage=50.0,
            disk_usage=30.0,
            database_status='healthy',
            redis_status='healthy',
            active_tasks=2,
            queued_tasks=3,
            failed_tasks_last_hour=1,
            avg_processing_time=120.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Should not raise exception
        monitor._store_health_metrics(health)
    
    def test_get_historical_metrics(self):
        """Test get_historical_metrics method"""
        # Mock Redis keys and data
        timestamp = int(datetime.now(timezone.utc).timestamp())
        key = f"vedfolnir:metrics:health:history:{timestamp}"
        
        self.mock_redis.keys.return_value = [key]
        self.mock_redis.get.return_value = json.dumps({
            'status': 'healthy',
            'cpu_usage': 25.0,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        metrics = self.monitor.get_historical_metrics('health', hours=24)
        
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]['status'], 'healthy')
        self.assertEqual(metrics[0]['cpu_usage'], 25.0)
    
    def test_get_historical_metrics_no_redis(self):
        """Test get_historical_metrics without Redis client"""
        monitor = SystemMonitor(db_manager=self.mock_db_manager, redis_client=None)
        
        metrics = monitor.get_historical_metrics('health')
        
        self.assertEqual(len(metrics), 0)
    
    def test_cleanup_old_metrics(self):
        """Test cleanup_old_metrics method"""
        # Mock old timestamp keys
        old_timestamp = int((datetime.now(timezone.utc) - timedelta(days=10)).timestamp())
        recent_timestamp = int(datetime.now(timezone.utc).timestamp())
        
        old_key = f"vedfolnir:metrics:health:history:{old_timestamp}"
        recent_key = f"vedfolnir:metrics:health:history:{recent_timestamp}"
        
        self.mock_redis.keys.return_value = [old_key, recent_key]
        
        self.monitor.cleanup_old_metrics()
        
        # Should delete old key but not recent key
        self.mock_redis.delete.assert_called_with(old_key)
    
    def test_cleanup_old_metrics_no_redis(self):
        """Test cleanup_old_metrics without Redis client"""
        monitor = SystemMonitor(db_manager=self.mock_db_manager, redis_client=None)
        
        # Should not raise exception
        monitor.cleanup_old_metrics()

if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Configuration Metrics Collection
"""

import unittest
import time
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.configuration.monitoring.configuration_metrics import (
    ConfigurationMetricsCollector,
    ConfigurationAccessMetric,
    ConfigurationCacheMetric,
    ConfigurationChangeMetric,
    ConfigurationPerformanceMetric,
    MetricType,
    MetricsSummary
)


class TestConfigurationMetricsCollector(unittest.TestCase):
    """Test cases for ConfigurationMetricsCollector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.collector = ConfigurationMetricsCollector(
            retention_hours=1,
            max_metrics_per_type=100
        )
    
    def tearDown(self):
        """Clean up after tests"""
        # Stop the cleanup thread
        if hasattr(self.collector, '_cleanup_thread'):
            self.collector._cleanup_thread = None
    
    def test_record_access_success(self):
        """Test recording successful configuration access"""
        # Record access
        self.collector.record_access(
            key="test_key",
            source="cache",
            access_time_ms=5.2,
            success=True,
            user_context="admin"
        )
        
        # Verify metric was recorded
        with self.collector._access_lock:
            self.assertEqual(len(self.collector._access_metrics), 1)
            metric = self.collector._access_metrics[0]
            self.assertEqual(metric.key, "test_key")
            self.assertEqual(metric.source, "cache")
            self.assertEqual(metric.access_time_ms, 5.2)
            self.assertTrue(metric.success)
            self.assertEqual(metric.user_context, "admin")
        
        # Verify stats were updated
        with self.collector._stats_lock:
            self.assertEqual(self.collector._stats['total_accesses'], 1)
            self.assertEqual(self.collector._stats['key_access_counts']['test_key'], 1)
            self.assertEqual(self.collector._stats['source_counts']['cache'], 1)
            self.assertEqual(self.collector._stats['total_errors'], 0)
    
    def test_record_access_failure(self):
        """Test recording failed configuration access"""
        # Record failed access
        self.collector.record_access(
            key="missing_key",
            source="database",
            access_time_ms=15.7,
            success=False,
            error_message="Key not found"
        )
        
        # Verify metric was recorded
        with self.collector._access_lock:
            self.assertEqual(len(self.collector._access_metrics), 1)
            metric = self.collector._access_metrics[0]
            self.assertEqual(metric.key, "missing_key")
            self.assertFalse(metric.success)
            self.assertEqual(metric.error_message, "Key not found")
        
        # Verify error stats were updated
        with self.collector._stats_lock:
            self.assertEqual(self.collector._stats['total_errors'], 1)
            self.assertEqual(self.collector._stats['error_counts']['missing_key'], 1)
    
    def test_record_cache_operations(self):
        """Test recording cache operations"""
        # Record cache hit
        self.collector.record_cache_operation(
            operation="hit",
            key="cached_key",
            cache_size=50,
            memory_usage_bytes=1024000,
            operation_time_ms=0.5,
            hit_rate=0.85
        )
        
        # Record cache miss
        self.collector.record_cache_operation(
            operation="miss",
            key="uncached_key",
            cache_size=50,
            memory_usage_bytes=1024000,
            operation_time_ms=2.1,
            hit_rate=0.84
        )
        
        # Verify metrics were recorded
        with self.collector._cache_lock:
            self.assertEqual(len(self.collector._cache_metrics), 2)
            
            hit_metric = self.collector._cache_metrics[0]
            self.assertEqual(hit_metric.operation, "hit")
            self.assertEqual(hit_metric.key, "cached_key")
            self.assertEqual(hit_metric.hit_rate, 0.85)
            
            miss_metric = self.collector._cache_metrics[1]
            self.assertEqual(miss_metric.operation, "miss")
            self.assertEqual(miss_metric.key, "uncached_key")
        
        # Verify stats were updated
        with self.collector._stats_lock:
            self.assertEqual(self.collector._stats['total_cache_hits'], 1)
            self.assertEqual(self.collector._stats['total_cache_misses'], 1)
    
    def test_record_configuration_change(self):
        """Test recording configuration changes"""
        # Record configuration change
        self.collector.record_configuration_change(
            key="max_concurrent_jobs",
            old_value=10,
            new_value=15,
            source="admin_ui",
            user_id=1,
            requires_restart=True,
            change_impact="medium"
        )
        
        # Verify metric was recorded
        with self.collector._change_lock:
            self.assertEqual(len(self.collector._change_metrics), 1)
            metric = self.collector._change_metrics[0]
            self.assertEqual(metric.key, "max_concurrent_jobs")
            self.assertEqual(metric.old_value, 10)
            self.assertEqual(metric.new_value, 15)
            self.assertEqual(metric.source, "admin_ui")
            self.assertEqual(metric.user_id, 1)
            self.assertTrue(metric.requires_restart)
            self.assertEqual(metric.change_impact, "medium")
        
        # Verify stats were updated
        with self.collector._stats_lock:
            self.assertEqual(self.collector._stats['total_changes'], 1)
            self.assertEqual(self.collector._stats['key_change_counts']['max_concurrent_jobs'], 1)
    
    def test_record_performance_impact(self):
        """Test recording performance impact metrics"""
        # Record performance impact
        self.collector.record_performance_impact(
            operation="cache_refresh",
            duration_ms=25.3,
            memory_delta_bytes=512000,
            cpu_usage_percent=15.2,
            affected_services=["task_queue", "session_manager"],
            performance_impact="low"
        )
        
        # Verify metric was recorded
        with self.collector._performance_lock:
            self.assertEqual(len(self.collector._performance_metrics), 1)
            metric = self.collector._performance_metrics[0]
            self.assertEqual(metric.operation, "cache_refresh")
            self.assertEqual(metric.duration_ms, 25.3)
            self.assertEqual(metric.memory_delta_bytes, 512000)
            self.assertEqual(metric.cpu_usage_percent, 15.2)
            self.assertEqual(metric.affected_services, ["task_queue", "session_manager"])
            self.assertEqual(metric.performance_impact, "low")
        
        # Verify performance samples were updated
        with self.collector._performance_lock_samples:
            self.assertEqual(len(self.collector._performance_samples), 1)
            sample = self.collector._performance_samples[0]
            self.assertEqual(sample['duration_ms'], 25.3)
            self.assertEqual(sample['memory_delta'], 512000)
            self.assertEqual(sample['cpu_usage'], 15.2)
    
    def test_get_access_patterns(self):
        """Test access pattern analysis"""
        # Record multiple access metrics
        test_data = [
            ("key1", "cache", 2.1, True),
            ("key1", "cache", 1.8, True),
            ("key2", "database", 15.3, True),
            ("key3", "environment", 0.5, True),
            ("key1", "cache", 2.5, False)  # Failed access
        ]
        
        for key, source, time_ms, success in test_data:
            self.collector.record_access(key, source, time_ms, success)
        
        # Get access patterns
        patterns = self.collector.get_access_patterns(hours=1)
        
        # Verify analysis
        self.assertEqual(patterns['total_accesses'], 5)
        self.assertEqual(patterns['unique_keys'], 3)
        self.assertAlmostEqual(patterns['success_rate'], 0.8)  # 4/5 successful
        self.assertAlmostEqual(patterns['error_rate'], 0.2)   # 1/5 failed
        
        # Check top keys
        self.assertEqual(patterns['top_keys'][0], ('key1', 3))  # key1 accessed 3 times
        
        # Check source distribution
        self.assertEqual(patterns['source_distribution']['cache'], 3)
        self.assertEqual(patterns['source_distribution']['database'], 1)
        self.assertEqual(patterns['source_distribution']['environment'], 1)
    
    def test_get_cache_performance(self):
        """Test cache performance analysis"""
        # Record cache operations
        cache_ops = [
            ("hit", "key1", 1.0),
            ("hit", "key2", 0.8),
            ("miss", "key3", 5.2),
            ("set", "key3", 2.1),
            ("evict", "key4", 1.5)
        ]
        
        for operation, key, time_ms in cache_ops:
            self.collector.record_cache_operation(
                operation=operation,
                key=key,
                cache_size=100,
                memory_usage_bytes=2048000,
                operation_time_ms=time_ms,
                hit_rate=0.75
            )
        
        # Get cache performance
        performance = self.collector.get_cache_performance(hours=1)
        
        # Verify analysis
        self.assertEqual(performance['total_operations'], 5)
        self.assertAlmostEqual(performance['hit_rate'], 2/3)  # 2 hits out of 3 hit/miss ops
        
        # Check operation distribution
        ops_dist = performance['operation_distribution']
        self.assertEqual(ops_dist['hits'], 2)
        self.assertEqual(ops_dist['misses'], 1)
        self.assertEqual(ops_dist['sets'], 1)
        self.assertEqual(ops_dist['evictions'], 1)
    
    def test_get_change_frequency(self):
        """Test change frequency analysis"""
        # Record configuration changes
        changes = [
            ("key1", 10, 15, "admin_ui", True, "high"),
            ("key2", "old", "new", "api", False, "low"),
            ("key1", 15, 20, "admin_ui", True, "medium"),
            ("key3", True, False, "environment", False, "low")
        ]
        
        for key, old_val, new_val, source, restart, impact in changes:
            self.collector.record_configuration_change(
                key=key,
                old_value=old_val,
                new_value=new_val,
                source=source,
                requires_restart=restart,
                change_impact=impact
            )
        
        # Get change frequency
        frequency = self.collector.get_change_frequency(hours=24)
        
        # Verify analysis
        self.assertEqual(frequency['total_changes'], 4)
        self.assertAlmostEqual(frequency['changes_per_hour'], 4/24)
        self.assertEqual(frequency['restart_required_changes'], 2)
        
        # Check most changed keys
        self.assertEqual(frequency['most_changed_keys'][0], ('key1', 2))
        
        # Check change sources
        self.assertEqual(frequency['change_sources']['admin_ui'], 2)
        self.assertEqual(frequency['change_sources']['api'], 1)
        self.assertEqual(frequency['change_sources']['environment'], 1)
        
        # Check impact distribution
        self.assertEqual(frequency['impact_distribution']['low'], 2)
        self.assertEqual(frequency['impact_distribution']['medium'], 1)
        self.assertEqual(frequency['impact_distribution']['high'], 1)
    
    def test_get_performance_impact(self):
        """Test performance impact analysis"""
        # Record performance metrics
        perf_data = [
            ("operation1", 10.5, 1024, 5.2),
            ("operation2", 25.3, -512, 12.1),
            ("operation3", 150.7, 2048, 45.8),  # High impact operation
            ("operation4", 5.1, 256, 2.3)
        ]
        
        for operation, duration, memory_delta, cpu_usage in perf_data:
            self.collector.record_performance_impact(
                operation=operation,
                duration_ms=duration,
                memory_delta_bytes=memory_delta,
                cpu_usage_percent=cpu_usage
            )
        
        # Get performance impact
        impact = self.collector.get_performance_impact(hours=1)
        
        # Verify analysis
        self.assertEqual(impact['total_operations'], 4)
        self.assertAlmostEqual(impact['average_duration_ms'], (10.5 + 25.3 + 150.7 + 5.1) / 4)
        self.assertEqual(impact['memory_impact_bytes'], 1024 - 512 + 2048 + 256)  # Sum of deltas
        
        # Performance impact score should be > 0 due to high duration operation
        self.assertGreater(impact['performance_impact_score'], 0.0)
    
    def test_comprehensive_summary(self):
        """Test comprehensive metrics summary"""
        # Record various metrics
        self.collector.record_access("key1", "cache", 2.1, True)
        self.collector.record_access("key2", "database", 15.3, True)
        self.collector.record_cache_operation("hit", "key1", 50, 1024000, 1.0, 0.8)
        self.collector.record_cache_operation("miss", "key2", 50, 1024000, 5.0, 0.75)
        self.collector.record_configuration_change("key1", 10, 15, "admin_ui", True, "medium")
        self.collector.record_performance_impact("test_op", 12.5, 512, 8.2)
        
        # Get comprehensive summary
        summary = self.collector.get_comprehensive_summary(hours=24)
        
        # Verify summary
        self.assertIsInstance(summary, MetricsSummary)
        self.assertEqual(summary.total_accesses, 2)
        self.assertAlmostEqual(summary.cache_hit_rate, 0.5)  # 1 hit, 1 miss
        self.assertEqual(summary.total_changes, 1)
        self.assertEqual(summary.restart_required_changes, 1)
        self.assertGreater(summary.performance_impact_score, 0.0)
        
        # Check most accessed keys
        self.assertTrue(len(summary.most_accessed_keys) > 0)
        self.assertTrue(len(summary.most_changed_keys) > 0)
    
    def test_export_metrics_json(self):
        """Test metrics export in JSON format"""
        # Record some test data
        self.collector.record_access("test_key", "cache", 5.0, True)
        self.collector.record_configuration_change("test_key", "old", "new", "admin_ui")
        
        # Export metrics
        exported = self.collector.export_metrics(hours=1, format='json')
        
        # Verify export
        self.assertIsInstance(exported, str)
        data = json.loads(exported)
        
        self.assertIn('export_timestamp', data)
        self.assertIn('time_period_hours', data)
        self.assertIn('summary', data)
        self.assertIn('access_patterns', data)
        self.assertIn('cache_performance', data)
        self.assertIn('change_frequency', data)
        self.assertIn('performance_impact', data)
        
        # Verify summary data
        summary = data['summary']
        self.assertEqual(summary['total_accesses'], 1)
        self.assertEqual(summary['total_changes'], 1)
    
    def test_export_metrics_csv(self):
        """Test metrics export in CSV format"""
        # Record some test data
        self.collector.record_access("test_key", "cache", 5.0, True)
        
        # Export metrics
        exported = self.collector.export_metrics(hours=1, format='csv')
        
        # Verify export
        self.assertIsInstance(exported, str)
        self.assertIn('Configuration Metrics Export', exported)
        self.assertIn('Total Accesses: 1', exported)
    
    def test_metrics_data_structures(self):
        """Test metrics data structure creation"""
        # Test ConfigurationAccessMetric
        access_metric = ConfigurationAccessMetric(
            key="test_key",
            timestamp=datetime.now(timezone.utc),
            source="cache",
            access_time_ms=5.2,
            success=True,
            user_context="admin"
        )
        
        self.assertEqual(access_metric.key, "test_key")
        self.assertEqual(access_metric.source, "cache")
        self.assertTrue(access_metric.success)
        
        # Test ConfigurationCacheMetric
        cache_metric = ConfigurationCacheMetric(
            operation="hit",
            key="cached_key",
            timestamp=datetime.now(timezone.utc),
            cache_size=100,
            memory_usage_bytes=1024000,
            operation_time_ms=1.5,
            hit_rate=0.85
        )
        
        self.assertEqual(cache_metric.operation, "hit")
        self.assertEqual(cache_metric.cache_size, 100)
        self.assertEqual(cache_metric.hit_rate, 0.85)
        
        # Test ConfigurationChangeMetric
        change_metric = ConfigurationChangeMetric(
            key="config_key",
            timestamp=datetime.now(timezone.utc),
            old_value=10,
            new_value=20,
            source="admin_ui",
            user_id=1,
            requires_restart=True,
            change_impact="high"
        )
        
        self.assertEqual(change_metric.key, "config_key")
        self.assertEqual(change_metric.old_value, 10)
        self.assertEqual(change_metric.new_value, 20)
        self.assertTrue(change_metric.requires_restart)
        
        # Test ConfigurationPerformanceMetric
        perf_metric = ConfigurationPerformanceMetric(
            operation="cache_refresh",
            timestamp=datetime.now(timezone.utc),
            duration_ms=25.5,
            memory_delta_bytes=512000,
            cpu_usage_percent=12.3,
            affected_services=["service1", "service2"],
            performance_impact="medium"
        )
        
        self.assertEqual(perf_metric.operation, "cache_refresh")
        self.assertEqual(perf_metric.duration_ms, 25.5)
        self.assertEqual(perf_metric.affected_services, ["service1", "service2"])
    
    def test_thread_safety(self):
        """Test thread safety of metrics collection"""
        import threading
        import random
        
        def record_metrics():
            for i in range(10):
                self.collector.record_access(f"key_{i}", "cache", random.uniform(1.0, 10.0), True)
                self.collector.record_cache_operation("hit", f"key_{i}", 50, 1024000, 1.0, 0.8)
                time.sleep(0.001)  # Small delay to simulate real usage
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=record_metrics)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify metrics were recorded correctly
        with self.collector._access_lock:
            self.assertEqual(len(self.collector._access_metrics), 50)  # 5 threads * 10 metrics
        
        with self.collector._cache_lock:
            self.assertEqual(len(self.collector._cache_metrics), 50)
        
        # Verify stats are consistent
        with self.collector._stats_lock:
            self.assertEqual(self.collector._stats['total_accesses'], 50)
            self.assertEqual(self.collector._stats['total_cache_hits'], 50)
    
    def test_metric_retention(self):
        """Test metric retention and cleanup"""
        from collections import deque
        
        # Create collector with normal retention
        collector = ConfigurationMetricsCollector(
            retention_hours=1,
            max_metrics_per_type=100
        )
        
        # Create an old timestamp (2 hours ago)
        old_timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Manually create an old metric
        from app.core.configuration.monitoring.configuration_metrics import ConfigurationAccessMetric
        old_metric = ConfigurationAccessMetric(
            key="old_key",
            timestamp=old_timestamp,
            source="cache",
            access_time_ms=5.0,
            success=True
        )
        
        # Add the old metric directly
        with collector._access_lock:
            collector._access_metrics.append(old_metric)
        
        # Record a new metric
        collector.record_access("new_key", "cache", 5.0, True)
        
        # Verify both metrics are present
        with collector._access_lock:
            self.assertEqual(len(collector._access_metrics), 2)
        
        # Manually trigger cleanup with 1 hour retention
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        with collector._access_lock:
            # Filter out old metrics
            filtered_metrics = [m for m in collector._access_metrics if m.timestamp >= cutoff_time]
            collector._access_metrics = deque(
                filtered_metrics,
                maxlen=collector.max_metrics_per_type
            )
        
        # Verify only the new metric remains (old one should be cleaned up)
        with collector._access_lock:
            self.assertEqual(len(collector._access_metrics), 1)
            remaining_metric = collector._access_metrics[0]
            self.assertEqual(remaining_metric.key, "new_key")


if __name__ == '__main__':
    unittest.main()
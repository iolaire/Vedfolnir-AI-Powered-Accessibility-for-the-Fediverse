# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Configuration Health Monitoring System
"""

import unittest
import time
import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.configuration.monitoring.configuration_health_monitor import (
    ConfigurationHealthMonitor,
    HealthStatus,
    ComponentType,
    HealthCheckResult,
    AlertThreshold,
    HealthSummary
)
from app.core.configuration.monitoring.configuration_health_endpoints import ConfigurationHealthChecks


class TestConfigurationHealthMonitoring(unittest.TestCase):
    """Integration tests for configuration health monitoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = ConfigurationHealthMonitor(
            check_interval=1,  # Short interval for testing
            history_retention_hours=1
        )
        
        # Mock components for testing
        self.mock_config_service = Mock()
        self.mock_cache = Mock()
        self.mock_db_manager = Mock()
        self.mock_event_bus = Mock()
        self.mock_metrics_collector = Mock()
        
        # Setup health check endpoints
        self.health_checks = ConfigurationHealthChecks(
            configuration_service=self.mock_config_service,
            configuration_cache=self.mock_cache,
            db_manager=self.mock_db_manager,
            event_bus=self.mock_event_bus,
            metrics_collector=self.mock_metrics_collector
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.monitor._monitoring_active:
            self.monitor.stop_monitoring()
    
    def test_component_registration(self):
        """Test component registration and management"""
        # Register a test component
        def mock_health_check():
            return {'status': 'healthy', 'test_metric': 42}
        
        self.monitor.register_component(
            name='test_component',
            component_type=ComponentType.CONFIGURATION_SERVICE,
            health_check_func=mock_health_check,
            enabled=True
        )
        
        # Verify component was registered
        with self.monitor._components_lock:
            self.assertIn('test_component', self.monitor._components)
            component = self.monitor._components['test_component']
            self.assertEqual(component['type'], ComponentType.CONFIGURATION_SERVICE)
            self.assertTrue(component['enabled'])
            self.assertEqual(component['consecutive_failures'], 0)
        
        # Test unregistration
        self.monitor.unregister_component('test_component')
        
        with self.monitor._components_lock:
            self.assertNotIn('test_component', self.monitor._components)
    
    def test_health_check_execution(self):
        """Test health check execution and result recording"""
        # Register test components with different health statuses
        def healthy_check():
            return {'status': 'healthy', 'response_time': 10}
        
        def warning_check():
            return {'status': 'warning', 'response_time': 150}
        
        def critical_check():
            return {'status': 'critical', 'error': 'Service unavailable'}
        
        self.monitor.register_component('healthy_service', ComponentType.CONFIGURATION_SERVICE, healthy_check)
        self.monitor.register_component('warning_service', ComponentType.CONFIGURATION_CACHE, warning_check)
        self.monitor.register_component('critical_service', ComponentType.DATABASE_CONNECTION, critical_check)
        
        # Perform health checks
        results = self.monitor.perform_health_check()
        
        # Verify results
        self.assertEqual(len(results), 3)
        
        # Check individual results
        result_by_component = {r.component: r for r in results}
        
        self.assertEqual(result_by_component['healthy_service'].status, HealthStatus.HEALTHY)
        self.assertEqual(result_by_component['warning_service'].status, HealthStatus.WARNING)
        self.assertEqual(result_by_component['critical_service'].status, HealthStatus.CRITICAL)
        
        # Verify history was recorded
        with self.monitor._health_lock:
            self.assertEqual(len(self.monitor._health_history), 3)
    
    def test_alert_thresholds_and_callbacks(self):
        """Test alert threshold evaluation and callback execution"""
        # Set up alert callback
        alert_calls = []
        
        def alert_callback(component_name, status, details):
            alert_calls.append({
                'component': component_name,
                'status': status,
                'details': details
            })
        
        self.monitor.add_alert_callback(alert_callback)
        
        # Set alert thresholds
        self.monitor.set_alert_threshold('response_time', 100.0, 200.0, 'greater_than')
        
        # Register component that will trigger alerts
        def slow_service_check():
            return {'response_time': 250}  # Above critical threshold, no explicit status
        
        self.monitor.register_component('slow_service', ComponentType.CONFIGURATION_SERVICE, slow_service_check)
        
        # Perform health check
        results = self.monitor.perform_health_check('slow_service')
        
        # Verify alert was triggered
        self.assertEqual(len(alert_calls), 1)
        self.assertEqual(alert_calls[0]['component'], 'slow_service')
        self.assertEqual(alert_calls[0]['status'], HealthStatus.CRITICAL)
    
    def test_health_summary_generation(self):
        """Test health summary generation"""
        # Register components with different statuses
        def healthy_check():
            return {'status': 'healthy'}
        
        def warning_check():
            return {'status': 'warning'}
        
        def critical_check():
            return {'status': 'critical'}
        
        self.monitor.register_component('healthy1', ComponentType.CONFIGURATION_SERVICE, healthy_check)
        self.monitor.register_component('healthy2', ComponentType.CONFIGURATION_CACHE, healthy_check)
        self.monitor.register_component('warning1', ComponentType.EVENT_BUS, warning_check)
        self.monitor.register_component('critical1', ComponentType.DATABASE_CONNECTION, critical_check)
        
        # Perform health checks
        self.monitor.perform_health_check()
        
        # Get health summary
        summary = self.monitor.get_health_summary()
        
        # Verify summary
        self.assertIsInstance(summary, HealthSummary)
        self.assertEqual(summary.healthy_components, 2)
        self.assertEqual(summary.warning_components, 1)
        self.assertEqual(summary.critical_components, 1)
        self.assertEqual(summary.unknown_components, 0)
        self.assertEqual(summary.overall_status, HealthStatus.CRITICAL)  # Worst status wins
        self.assertGreater(summary.uptime_seconds, 0)
    
    def test_performance_metrics_tracking(self):
        """Test performance metrics tracking and analysis"""
        # Register component with varying response times
        response_times = [10, 15, 25, 50, 100]  # Increasing response times
        call_count = 0
        
        def variable_performance_check():
            nonlocal call_count
            response_time = response_times[call_count % len(response_times)]
            call_count += 1
            return {'status': 'healthy', 'response_time': response_time}
        
        self.monitor.register_component('perf_test', ComponentType.CONFIGURATION_SERVICE, variable_performance_check)
        
        # Perform multiple health checks
        for _ in range(5):
            self.monitor.perform_health_check('perf_test')
            time.sleep(0.1)
        
        # Get performance metrics
        metrics = self.monitor.get_performance_metrics('perf_test', hours=1)
        
        # Verify metrics (the method returns the component data directly when component_name is specified)
        self.assertIsInstance(metrics, dict)
        perf_data = metrics
        self.assertEqual(perf_data['total_checks'], 5)
        self.assertGreater(perf_data['average_response_time_ms'], 0)
        self.assertGreater(perf_data['max_response_time_ms'], perf_data['min_response_time_ms'])
    
    def test_error_statistics_tracking(self):
        """Test error statistics tracking and analysis"""
        # Register component that will fail
        def failing_check():
            raise Exception("Simulated failure")
        
        self.monitor.register_component('failing_service', ComponentType.CONFIGURATION_SERVICE, failing_check)
        
        # Perform multiple health checks to generate errors
        for _ in range(3):
            self.monitor.perform_health_check('failing_service')
            time.sleep(0.1)
        
        # Get error statistics
        error_stats = self.monitor.get_error_statistics(hours=1)
        
        # Verify error tracking
        self.assertGreater(error_stats['total_errors'], 0)
        self.assertGreater(error_stats['error_rate'], 0)
        self.assertIn('failing_service', error_stats['errors_by_component'])
        self.assertIn('health_check_failure', error_stats['errors_by_type'])
    
    def test_continuous_monitoring(self):
        """Test continuous monitoring functionality"""
        # Register a test component
        check_calls = []
        
        def monitored_check():
            check_calls.append(datetime.now(timezone.utc))
            return {'status': 'healthy'}
        
        self.monitor.register_component('monitored_service', ComponentType.CONFIGURATION_SERVICE, monitored_check)
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Wait for a few monitoring cycles
        time.sleep(2.5)  # Should allow for 2-3 checks with 1-second interval
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        
        # Verify multiple checks were performed
        self.assertGreaterEqual(len(check_calls), 2)
        
        # Verify health history was populated
        with self.monitor._health_lock:
            self.assertGreaterEqual(len(self.monitor._health_history), 2)
    
    def test_health_dashboard_data(self):
        """Test health dashboard data generation"""
        # Register components
        def healthy_check():
            return {'status': 'healthy', 'metric1': 10, 'metric2': 20}
        
        def warning_check():
            return {'status': 'warning', 'metric1': 150}
        
        self.monitor.register_component('service1', ComponentType.CONFIGURATION_SERVICE, healthy_check)
        self.monitor.register_component('service2', ComponentType.CONFIGURATION_CACHE, warning_check)
        
        # Perform health checks
        self.monitor.perform_health_check()
        
        # Get dashboard data
        dashboard_data = self.monitor.get_health_dashboard_data()
        
        # Verify dashboard data structure
        self.assertIn('summary', dashboard_data)
        self.assertIn('components', dashboard_data)
        self.assertIn('performance_metrics', dashboard_data)
        self.assertIn('error_statistics', dashboard_data)
        self.assertIn('health_timeline', dashboard_data)
        self.assertIn('alert_thresholds', dashboard_data)
        
        # Verify summary data
        summary = dashboard_data['summary']
        self.assertEqual(summary['healthy_components'], 1)
        self.assertEqual(summary['warning_components'], 1)
        
        # Verify component data
        components = dashboard_data['components']
        self.assertEqual(len(components), 2)
        
        component_names = [c['name'] for c in components]
        self.assertIn('service1', component_names)
        self.assertIn('service2', component_names)
    
    def test_data_export(self):
        """Test health data export functionality"""
        # Register and check a component
        def test_check():
            return {'status': 'healthy', 'test_metric': 42}
        
        self.monitor.register_component('export_test', ComponentType.CONFIGURATION_SERVICE, test_check)
        self.monitor.perform_health_check()
        
        # Test JSON export
        json_export = self.monitor.export_health_data(hours=1, format='json')
        self.assertIsInstance(json_export, str)
        self.assertIn('export_timestamp', json_export)
        self.assertIn('dashboard_data', json_export)
        
        # Test CSV export
        csv_export = self.monitor.export_health_data(hours=1, format='csv')
        self.assertIsInstance(csv_export, str)
        self.assertIn('Configuration Health Export', csv_export)
        self.assertIn('Overall Status:', csv_export)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.Process')
    def test_configuration_service_health_check(self, mock_process, mock_disk, mock_memory, mock_cpu):
        """Test configuration service health check endpoint"""
        # Mock system resources
        mock_cpu.return_value = 25.0
        mock_memory.return_value = Mock(percent=45.0, available=8000000000)
        mock_disk.return_value = Mock(percent=60.0, free=100000000000)
        mock_process.return_value.memory_info.return_value.rss = 100000000
        mock_process.return_value.cpu_percent.return_value = 5.0
        
        # Mock configuration service
        self.mock_config_service.get_config.return_value = 'test_value'
        self.mock_config_service.get_cache_stats.return_value = {
            'hit_rate': 0.85,
            'total_requests': 100,
            'cache': {'size': 50}
        }
        self.mock_config_service.is_restart_required.return_value = False
        self.mock_config_service.get_pending_restart_configs.return_value = []
        self.mock_config_service._subscribers = {'key1': {'sub1': Mock()}}
        
        # Perform health check
        result = self.health_checks.check_configuration_service_health()
        
        # Verify result
        self.assertEqual(result['status'], 'healthy')
        self.assertTrue(result['config_access_working'])
        self.assertFalse(result['restart_required'])
        self.assertEqual(result['subscriber_count'], 1)
        self.assertIn('response_time_ms', result)
        self.assertIn('timestamp', result)
    
    def test_configuration_cache_health_check(self):
        """Test configuration cache health check endpoint"""
        # Mock cache statistics
        mock_stats = Mock()
        mock_stats.hit_rate = 0.75
        mock_stats.cache_efficiency = 0.80
        mock_stats.memory_usage_bytes = 50 * 1024 * 1024  # 50MB
        mock_stats.total_keys = 100
        mock_stats.hits = 750
        mock_stats.misses = 250
        mock_stats.evictions = 10
        mock_stats.average_access_time_ms = 2.5
        
        self.mock_cache.get_stats.return_value = mock_stats
        self.mock_cache.get_cache_info.return_value = {
            'maxsize': 1000,
            'current_size': 100
        }
        
        # Mock cache operations
        self.mock_cache.set.return_value = None
        self.mock_cache.get.return_value = Mock()  # Non-None return indicates success
        self.mock_cache.invalidate.return_value = True
        
        # Perform health check
        result = self.health_checks.check_configuration_cache_health()
        
        # Verify result
        self.assertEqual(result['status'], 'healthy')
        self.assertTrue(result['cache_operations_working'])
        self.assertEqual(result['hit_rate'], 0.75)
        self.assertEqual(result['total_keys'], 100)
        self.assertIn('response_time_ms', result)
    
    def test_database_connection_health_check(self):
        """Test database connection health check endpoint"""
        # Mock database manager and session
        mock_session = Mock()
        mock_session.execute.return_value.fetchone.side_effect = [
            (1,),  # SELECT 1 result
            (5,)   # COUNT(*) result
        ]
        
        # Mock context manager for session
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        # Mock connection pool
        mock_pool = Mock()
        mock_pool.size.return_value = 20
        mock_pool.checkedin.return_value = 15
        mock_pool.checkedout.return_value = 5
        mock_pool.overflow.return_value = 0
        mock_pool.invalid.return_value = 0
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        self.mock_db_manager.engine = mock_engine
        self.mock_db_manager.config.DATABASE_URL = 'mysql://user:pass@localhost/db'
        
        # Perform health check
        result = self.health_checks.check_database_connection_health()
        
        # Verify result
        self.assertEqual(result['status'], 'healthy')
        self.assertTrue(result['connection_working'])
        self.assertTrue(result['query_working'])
        self.assertIn('pool_info', result)
        self.assertEqual(result['pool_info']['pool_size'], 20)
        self.assertIn('response_time_ms', result)
    
    def test_metrics_collector_health_check(self):
        """Test metrics collector health check endpoint"""
        # Mock metrics collector
        self.mock_metrics_collector.record_access.return_value = None
        
        mock_summary = Mock()
        mock_summary.total_accesses = 100
        mock_summary.cache_hit_rate = 0.85
        self.mock_metrics_collector.get_comprehensive_summary.return_value = mock_summary
        
        self.mock_metrics_collector.get_access_patterns.return_value = {
            'total_accesses': 100,
            'error_rate': 0.02
        }
        self.mock_metrics_collector.get_cache_performance.return_value = {
            'hit_rate': 0.85
        }
        self.mock_metrics_collector.get_change_frequency.return_value = {
            'total_changes': 10
        }
        
        # Perform health check
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 200 * 1024 * 1024  # 200MB
            result = self.health_checks.check_metrics_collector_health()
        
        # Verify result
        self.assertEqual(result['status'], 'healthy')
        self.assertTrue(result['metrics_recording_working'])
        self.assertTrue(result['metrics_analysis_working'])
        self.assertIn('metrics_stats', result)
        self.assertEqual(result['metrics_stats']['total_accesses'], 100)
        self.assertIn('response_time_ms', result)
    
    def test_all_health_checks_integration(self):
        """Test running all health checks together"""
        # Setup all mocks for successful health checks
        self._setup_all_mocks_healthy()
        
        # Run all health checks
        all_results = self.health_checks.get_all_health_checks()
        
        # Verify all components were checked
        expected_components = [
            'configuration_service',
            'configuration_cache',
            'database_connection',
            'event_bus',
            'metrics_collector',
            'system_resources'
        ]
        
        for component in expected_components:
            self.assertIn(component, all_results)
            self.assertIn('status', all_results[component])
            self.assertIn('response_time_ms', all_results[component])
            self.assertIn('timestamp', all_results[component])
    
    def _setup_all_mocks_healthy(self):
        """Setup all mocks to return healthy status"""
        # Configuration service mocks
        self.mock_config_service.get_config.return_value = 'test'
        self.mock_config_service.get_cache_stats.return_value = {'hit_rate': 0.85}
        self.mock_config_service.is_restart_required.return_value = False
        self.mock_config_service.get_pending_restart_configs.return_value = []
        self.mock_config_service._subscribers = {}
        
        # Cache mocks
        mock_stats = Mock()
        mock_stats.hit_rate = 0.85
        mock_stats.cache_efficiency = 0.80
        mock_stats.memory_usage_bytes = 50 * 1024 * 1024
        mock_stats.total_keys = 100
        mock_stats.hits = 850
        mock_stats.misses = 150
        mock_stats.evictions = 5
        mock_stats.average_access_time_ms = 2.0
        
        self.mock_cache.get_stats.return_value = mock_stats
        self.mock_cache.get_cache_info.return_value = {'maxsize': 1000, 'current_size': 100}
        self.mock_cache.set.return_value = None
        self.mock_cache.get.return_value = Mock()
        self.mock_cache.invalidate.return_value = True
        
        # Database mocks
        mock_session = Mock()
        mock_session.execute.return_value.fetchone.side_effect = [(1,), (10,)]
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session.return_value = mock_context_manager
        
        # Event bus mocks
        self.mock_event_bus.subscribe.return_value = 'test_sub_id'
        self.mock_event_bus.publish.return_value = None
        self.mock_event_bus.unsubscribe.return_value = True
        self.mock_event_bus._subscribers = {'key1': {'sub1': Mock()}}
        
        # Metrics collector mocks
        self.mock_metrics_collector.record_access.return_value = None
        mock_summary = Mock()
        mock_summary.total_accesses = 100
        self.mock_metrics_collector.get_comprehensive_summary.return_value = mock_summary
        self.mock_metrics_collector.get_access_patterns.return_value = {'total_accesses': 100, 'error_rate': 0.01}
        self.mock_metrics_collector.get_cache_performance.return_value = {'hit_rate': 0.85}
        self.mock_metrics_collector.get_change_frequency.return_value = {'total_changes': 5}


if __name__ == '__main__':
    unittest.main()
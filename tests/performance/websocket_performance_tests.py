# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Performance Monitoring Tests

Comprehensive test suite for WebSocket performance monitoring,
optimization, and scalability testing components.
"""

import unittest
import time
import asyncio
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from websocket_performance_monitor import (
    WebSocketPerformanceMonitor, LoadLevel, PerformanceLevel,
    ConnectionPoolMetrics, MessageDeliveryMetrics, ResourceUsageMetrics
)
from websocket_performance_optimizer import (
    WebSocketPerformanceOptimizer, OptimizationStrategy, OptimizationAction,
    OptimizationRule, OptimizationResult
)
from websocket_scalability_tester import (
    WebSocketScalabilityTester, LoadTestConfig, TestResult,
    create_load_test_config
)


class TestWebSocketPerformanceMonitor(unittest.TestCase):
    """Test WebSocket performance monitoring functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = WebSocketPerformanceMonitor(monitoring_interval=1)
        
    def tearDown(self):
        """Clean up after tests"""
        if self.monitor.monitoring_active:
            self.monitor.stop_monitoring()
            
    def test_monitor_initialization(self):
        """Test monitor initialization"""
        self.assertEqual(self.monitor.monitoring_interval, 1)
        self.assertFalse(self.monitor.monitoring_active)
        self.assertEqual(len(self.monitor.active_connections), 0)
        
    def test_connection_registration(self):
        """Test connection registration and unregistration"""
        # Register connection
        connection_info = {
            'namespace': '/',
            'transport': 'websocket',
            'user_agent': 'test_client'
        }
        
        self.monitor.register_connection('test_conn_1', connection_info)
        
        self.assertEqual(len(self.monitor.active_connections), 1)
        self.assertIn('test_conn_1', self.monitor.active_connections)
        self.assertEqual(self.monitor.stats['total_connections_created'], 1)
        
        # Unregister connection
        self.monitor.unregister_connection('test_conn_1', 'test_disconnect')
        
        self.assertEqual(len(self.monitor.active_connections), 0)
        self.assertEqual(self.monitor.stats['total_connections_destroyed'], 1)
        
    def test_message_recording(self):
        """Test message recording functionality"""
        # Register connection first
        self.monitor.register_connection('test_conn_1', {})
        
        # Record messages
        self.monitor.record_message_sent('test_conn_1', 1024, 50.0)
        self.monitor.record_message_received('test_conn_1', 512)
        
        conn = self.monitor.active_connections['test_conn_1']
        self.assertEqual(conn['messages_sent'], 1)
        self.assertEqual(conn['messages_received'], 1)
        self.assertEqual(conn['bytes_sent'], 1024)
        self.assertEqual(conn['bytes_received'], 512)
        
    def test_error_recording(self):
        """Test error recording functionality"""
        self.monitor.register_connection('test_conn_1', {})
        
        self.monitor.record_error('test_conn_1', 'connection_error', {'details': 'test error'})
        
        conn = self.monitor.active_connections['test_conn_1']
        self.assertEqual(conn['errors'], 1)
        self.assertEqual(self.monitor.stats['total_errors'], 1)
        
    def test_performance_summary(self):
        """Test performance summary generation"""
        # Add some test data
        self.monitor.register_connection('test_conn_1', {})
        self.monitor.record_message_sent('test_conn_1', 1024, 50.0)
        self.monitor.record_latency_sample('test_conn_1', 100.0)
        
        summary = self.monitor.get_current_performance_summary()
        
        self.assertIn('performance_level', summary)
        self.assertIn('connection_pool', summary)
        self.assertIn('message_delivery', summary)
        self.assertIn('resource_usage', summary)
        self.assertIn('connection_quality', summary)
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_resource_metrics_collection(self, mock_memory, mock_cpu):
        """Test resource metrics collection"""
        # Mock system metrics
        mock_cpu.return_value = 75.0
        mock_memory.return_value = Mock(percent=80.0, available=1024*1024*1024)
        
        metrics = self.monitor._collect_resource_metrics()
        
        self.assertEqual(metrics.cpu_usage, 75.0)
        self.assertEqual(metrics.memory_usage, 80.0)
        self.assertEqual(metrics.memory_available, 1024*1024*1024)
        
    def test_scalability_metrics(self):
        """Test scalability metrics calculation"""
        # Add some connections
        for i in range(10):
            self.monitor.register_connection(f'conn_{i}', {})
            
        scalability = self.monitor.get_scalability_metrics()
        
        self.assertIn('current_load_level', scalability)
        self.assertIn('current_connections', scalability)
        self.assertIn('estimated_max_connections', scalability)
        self.assertIn('scaling_factor', scalability)
        
    def test_monitoring_thread(self):
        """Test monitoring thread functionality"""
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor.monitoring_active)
        
        # Let it run briefly
        time.sleep(2)
        
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor.monitoring_active)


class TestWebSocketPerformanceOptimizer(unittest.TestCase):
    """Test WebSocket performance optimization functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = Mock(spec=WebSocketPerformanceMonitor)
        self.optimizer = WebSocketPerformanceOptimizer(
            self.monitor, 
            OptimizationStrategy.BALANCED
        )
        
    def tearDown(self):
        """Clean up after tests"""
        if self.optimizer.optimization_active:
            self.optimizer.stop_auto_optimization()
            
    def test_optimizer_initialization(self):
        """Test optimizer initialization"""
        self.assertEqual(self.optimizer.strategy, OptimizationStrategy.BALANCED)
        self.assertFalse(self.optimizer.optimization_active)
        self.assertIn('max_connections', self.optimizer.current_settings)
        
    def test_optimization_rules_creation(self):
        """Test optimization rules creation"""
        rules = self.optimizer.optimization_rules
        
        self.assertGreater(len(rules), 0)
        
        # Check that all rules have required attributes
        for rule in rules:
            self.assertIsInstance(rule.name, str)
            self.assertIsInstance(rule.action, OptimizationAction)
            self.assertIsInstance(rule.priority, int)
            self.assertIsInstance(rule.cooldown_seconds, int)
            
    def test_optimization_recommendations(self):
        """Test optimization recommendations"""
        # Mock performance data that should trigger recommendations
        mock_performance = {
            'resource_usage': {'cpu_usage': 90, 'memory_usage': 85},
            'connection_quality': {'error_rate': 0.15, 'avg_latency': 300},
            'connection_pool': {'utilization': 0.9}
        }
        
        self.monitor.get_current_performance_summary.return_value = mock_performance
        
        recommendations = self.optimizer.get_optimization_recommendations()
        
        self.assertIsInstance(recommendations, list)
        # Should have recommendations due to high resource usage
        self.assertGreater(len(recommendations), 0)
        
    def test_optimization_simulation(self):
        """Test optimization simulation"""
        # Mock performance data
        mock_performance = {
            'resource_usage': {'cpu_usage': 85, 'memory_usage': 80},
            'connection_quality': {'error_rate': 0.05, 'avg_latency': 150}
        }
        
        self.monitor.get_current_performance_summary.return_value = mock_performance
        
        # Get first rule name
        rule_name = self.optimizer.optimization_rules[0].name
        
        simulation = self.optimizer.simulate_optimization(rule_name)
        
        self.assertIn('rule_name', simulation)
        self.assertIn('current_settings', simulation)
        self.assertIn('simulated_settings', simulation)
        self.assertIn('estimated_impact', simulation)
        
    def test_settings_modification(self):
        """Test settings modification methods"""
        original_max_connections = self.optimizer.current_settings['max_connections']
        
        # Test increase limits
        self.optimizer._increase_limits({'max_connections': lambda x: x * 2})
        self.assertEqual(
            self.optimizer.current_settings['max_connections'], 
            original_max_connections * 2
        )
        
        # Test decrease limits
        self.optimizer._decrease_limits({'max_connections': lambda x: x // 2})
        self.assertEqual(
            self.optimizer.current_settings['max_connections'], 
            original_max_connections
        )
        
    def test_auto_optimization_thread(self):
        """Test auto-optimization thread"""
        # Mock performance data
        self.monitor.get_current_performance_summary.return_value = {
            'resource_usage': {'cpu_usage': 50, 'memory_usage': 60},
            'connection_quality': {'error_rate': 0.02, 'avg_latency': 100}
        }
        
        self.optimizer.start_auto_optimization()
        self.assertTrue(self.optimizer.optimization_active)
        
        # Let it run briefly
        time.sleep(2)
        
        self.optimizer.stop_auto_optimization()
        self.assertFalse(self.optimizer.optimization_active)


class TestWebSocketScalabilityTester(unittest.TestCase):
    """Test WebSocket scalability testing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tester = WebSocketScalabilityTester()
        
    def test_tester_initialization(self):
        """Test tester initialization"""
        self.assertEqual(len(self.tester.test_results), 0)
        self.assertEqual(len(self.tester.active_tests), 0)
        
    def test_load_test_config_creation(self):
        """Test load test configuration creation"""
        config = create_load_test_config('http://localhost:5000', 100, 60)
        
        self.assertEqual(config.target_url, 'http://localhost:5000')
        self.assertEqual(config.max_connections, 100)
        self.assertEqual(config.steady_state_duration, 60)
        self.assertIsInstance(config.namespaces, list)
        
    @patch('socketio.AsyncClient')
    def test_load_test_execution(self, mock_client_class):
        """Test load test execution (mocked)"""
        # Mock SocketIO client
        mock_client = Mock()
        mock_client.connect = Mock(return_value=None)
        mock_client.disconnect = Mock(return_value=None)
        mock_client.emit = Mock(return_value=None)
        mock_client_class.return_value = mock_client
        
        # Create test configuration
        config = LoadTestConfig(
            target_url='http://localhost:5000',
            max_connections=2,  # Small number for testing
            ramp_up_duration=1,
            steady_state_duration=1,
            ramp_down_duration=1,
            messages_per_connection=2,
            message_interval=0.1,
            connection_timeout=5,
            namespaces=['/'],
            test_data_size=100
        )
        
        # Run test using asyncio.run for proper async handling
        async def run_test():
            return await self.tester.run_load_test(config)
        
        result = asyncio.run(run_test())
        
        self.assertIsInstance(result.test_name, str)
        self.assertEqual(result.config, config)
        self.assertIsInstance(result.result, TestResult)
        
    def test_aggregate_metrics_calculation(self):
        """Test aggregate metrics calculation"""
        from websocket_scalability_tester import ConnectionMetrics
        
        # Create mock connection metrics
        metrics = [
            ConnectionMetrics(
                connection_id='conn_1',
                connected_at=datetime.now(timezone.utc),
                disconnected_at=None,
                connection_time=0.5,
                messages_sent=10,
                messages_received=8,
                errors=[],
                latency_samples=[50.0, 60.0, 55.0],
                status='connected'
            ),
            ConnectionMetrics(
                connection_id='conn_2',
                connected_at=datetime.now(timezone.utc),
                disconnected_at=None,
                connection_time=0.7,
                messages_sent=12,
                messages_received=10,
                errors=['timeout'],
                latency_samples=[70.0, 80.0],
                status='connected'
            )
        ]
        
        aggregate = self.tester._calculate_aggregate_metrics(metrics)
        
        self.assertEqual(aggregate['total_connections'], 2)
        self.assertEqual(aggregate['successful_connections'], 2)
        self.assertEqual(aggregate['total_messages_sent'], 22)
        self.assertEqual(aggregate['total_messages_received'], 18)
        self.assertGreater(aggregate['connection_time_avg'], 0)
        self.assertGreater(aggregate['latency_avg'], 0)
        
    def test_performance_summary_generation(self):
        """Test performance summary generation"""
        aggregate_metrics = {
            'connection_success_rate': 0.95,
            'message_success_rate': 0.90,
            'latency_avg': 75.0,
            'error_rate': 0.05,
            'total_messages_sent': 100
        }
        
        summary = self.tester._generate_performance_summary(aggregate_metrics)
        
        self.assertIn('performance_level', summary)
        self.assertIn('performance_score', summary)
        self.assertIn('connection_success_rate', summary)
        self.assertIn('message_success_rate', summary)
        self.assertIn('avg_latency_ms', summary)
        
    def test_result_analysis(self):
        """Test test result analysis"""
        from websocket_scalability_tester import ScalabilityTestResult
        
        # Create mock result with poor performance
        result = ScalabilityTestResult(
            test_name='test',
            config=create_load_test_config('http://localhost:5000', 100),
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            total_duration=60.0,
            phase_durations={},
            connection_metrics=[],
            aggregate_metrics={
                'connection_success_rate': 0.7,  # Low success rate
                'message_success_rate': 0.8,
                'latency_avg': 600.0,  # High latency
                'error_rate': 0.15  # High error rate
            },
            performance_summary={'performance_level': 'poor'},
            result=TestResult.PASS,  # Will be overridden
            issues=[],
            recommendations=[]
        )
        
        test_result, issues, recommendations = self.tester._analyze_test_results(result)
        
        self.assertEqual(test_result, TestResult.FAIL)
        self.assertGreater(len(issues), 0)
        self.assertGreater(len(recommendations), 0)


class TestPerformanceIntegration(unittest.TestCase):
    """Test integration between performance components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = WebSocketPerformanceMonitor(monitoring_interval=1)
        self.optimizer = WebSocketPerformanceOptimizer(self.monitor)
        
    def tearDown(self):
        """Clean up after tests"""
        if self.monitor.monitoring_active:
            self.monitor.stop_monitoring()
        if self.optimizer.optimization_active:
            self.optimizer.stop_auto_optimization()
            
    def test_monitor_optimizer_integration(self):
        """Test integration between monitor and optimizer"""
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Add some load to trigger optimization
        for i in range(50):
            self.monitor.register_connection(f'conn_{i}', {})
            self.monitor.record_message_sent(f'conn_{i}', 1024, 100.0)
            
        # Get performance summary
        performance = self.monitor.get_current_performance_summary()
        
        # Get optimization recommendations
        recommendations = self.optimizer.get_optimization_recommendations()
        
        self.assertIsInstance(performance, dict)
        self.assertIsInstance(recommendations, list)
        
    def test_callback_integration(self):
        """Test callback integration between components"""
        callback_called = False
        callback_data = None
        
        def test_callback(data):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = data
            
        # Add callback to monitor
        self.monitor.add_performance_callback(test_callback)
        
        # Start monitoring briefly
        self.monitor.start_monitoring()
        time.sleep(2)
        self.monitor.stop_monitoring()
        
        # Check if callback was called
        self.assertTrue(callback_called)
        self.assertIsNotNone(callback_data)


if __name__ == '__main__':
    # Set up test logging
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run tests
    unittest.main(verbosity=2)
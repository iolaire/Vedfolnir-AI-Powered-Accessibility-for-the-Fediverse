# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Performance and Load Testing

This module provides comprehensive performance and load testing for the WebSocket
CORS standardization system, including connection load testing, message throughput
testing, memory usage monitoring, and scalability testing under high load conditions.
"""

import unittest
import os
import sys
import time
import threading
import psutil
import gc
import statistics
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_auth_handler import WebSocketAuthHandler, AuthenticationResult
from websocket_factory import WebSocketFactory
from session_manager_v2 import SessionManagerV2
from app.core.database.core.database_manager import DatabaseManager


class PerformanceMetrics:
    """Performance metrics collector for WebSocket testing"""
    
    def __init__(self):
        self.reset_metrics()
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        self.response_times = []
        self.throughput_data = []
        self.memory_usage = []
        self.cpu_usage = []
        self.error_count = 0
        self.success_count = 0
        self.start_time = None
        self.end_time = None
    
    def start_measurement(self):
        """Start performance measurement"""
        self.start_time = time.time()
        self.reset_metrics()
    
    def end_measurement(self):
        """End performance measurement"""
        self.end_time = time.time()
    
    def record_response_time(self, response_time: float):
        """Record a response time measurement"""
        self.response_times.append(response_time)
    
    def record_success(self):
        """Record a successful operation"""
        self.success_count += 1
    
    def record_error(self):
        """Record an error"""
        self.error_count += 1
    
    def record_memory_usage(self):
        """Record current memory usage"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.memory_usage.append(memory_mb)
    
    def record_cpu_usage(self):
        """Record current CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.cpu_usage.append(cpu_percent)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        total_operations = self.success_count + self.error_count
        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        
        summary = {
            'duration_seconds': duration,
            'total_operations': total_operations,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': (self.success_count / total_operations * 100) if total_operations > 0 else 0,
            'operations_per_second': total_operations / duration if duration > 0 else 0,
        }
        
        if self.response_times:
            summary.update({
                'avg_response_time_ms': statistics.mean(self.response_times) * 1000,
                'min_response_time_ms': min(self.response_times) * 1000,
                'max_response_time_ms': max(self.response_times) * 1000,
                'median_response_time_ms': statistics.median(self.response_times) * 1000,
                'p95_response_time_ms': self._percentile(self.response_times, 95) * 1000,
                'p99_response_time_ms': self._percentile(self.response_times, 99) * 1000,
            })
        
        if self.memory_usage:
            summary.update({
                'avg_memory_mb': statistics.mean(self.memory_usage),
                'max_memory_mb': max(self.memory_usage),
                'min_memory_mb': min(self.memory_usage),
            })
        
        if self.cpu_usage:
            summary.update({
                'avg_cpu_percent': statistics.mean(self.cpu_usage),
                'max_cpu_percent': max(self.cpu_usage),
            })
        
        return summary
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class TestWebSocketConfigurationPerformance(unittest.TestCase):
    """Performance tests for WebSocket configuration components"""
    
    def setUp(self):
        """Set up configuration performance test environment"""
        self.config = Config()
        self.metrics = PerformanceMetrics()
    
    def test_configuration_loading_performance(self):
        """Test configuration loading performance under load"""
        self.metrics.start_measurement()
        
        # Test configuration loading performance
        for i in range(1000):
            start_time = time.time()
            
            config_manager = WebSocketConfigManager(self.config)
            cors_origins = config_manager.get_cors_origins()
            socketio_config = config_manager.get_socketio_config()
            client_config = config_manager.get_client_config()
            
            end_time = time.time()
            self.metrics.record_response_time(end_time - start_time)
            
            if cors_origins and socketio_config and client_config:
                self.metrics.record_success()
            else:
                self.metrics.record_error()
            
            # Record system metrics every 100 iterations
            if i % 100 == 0:
                self.metrics.record_memory_usage()
                self.metrics.record_cpu_usage()
        
        self.metrics.end_measurement()
        summary = self.metrics.get_summary()
        
        # Performance assertions
        self.assertLess(summary['avg_response_time_ms'], 50, "Average config loading should be under 50ms")
        self.assertGreater(summary['operations_per_second'], 20, "Should handle at least 20 config loads per second")
        self.assertGreater(summary['success_rate'], 99, "Success rate should be above 99%")
        
        print(f"\n📊 Configuration Loading Performance:")
        print(f"   Average response time: {summary['avg_response_time_ms']:.2f}ms")
        print(f"   Operations per second: {summary['operations_per_second']:.1f}")
        print(f"   Success rate: {summary['success_rate']:.1f}%")
    
    def test_cors_validation_performance(self):
        """Test CORS validation performance under high load"""
        config_manager = WebSocketConfigManager(self.config)
        cors_manager = CORSManager(config_manager)
        
        # Prepare test origins
        test_origins = [
            'http://localhost:5000',
            'https://127.0.0.1:5000',
            'http://localhost:3000',
            'https://example.com',
            'http://malicious.com',
            'invalid-origin',
            'http://localhost:8080',
            'https://app.example.com',
        ] * 125  # 1000 total validations
        
        self.metrics.start_measurement()
        
        for i, origin in enumerate(test_origins):
            start_time = time.time()
            
            is_valid = cors_manager.validate_origin(origin)
            
            end_time = time.time()
            self.metrics.record_response_time(end_time - start_time)
            self.metrics.record_success()  # All validations are successful operations
            
            # Record system metrics every 200 iterations
            if i % 200 == 0:
                self.metrics.record_memory_usage()
                self.metrics.record_cpu_usage()
        
        self.metrics.end_measurement()
        summary = self.metrics.get_summary()
        
        # Performance assertions
        self.assertLess(summary['avg_response_time_ms'], 5, "Average CORS validation should be under 5ms")
        self.assertGreater(summary['operations_per_second'], 500, "Should handle at least 500 validations per second")
        
        print(f"\n📊 CORS Validation Performance:")
        print(f"   Average response time: {summary['avg_response_time_ms']:.2f}ms")
        print(f"   Operations per second: {summary['operations_per_second']:.1f}")
        print(f"   P95 response time: {summary['p95_response_time_ms']:.2f}ms")
    
    def test_configuration_memory_efficiency(self):
        """Test configuration memory efficiency"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many configuration managers
        config_managers = []
        for i in range(100):
            config_manager = WebSocketConfigManager(self.config)
            cors_manager = CORSManager(config_manager)
            config_managers.append((config_manager, cors_manager))
            
            # Trigger configuration loading
            config_manager.get_cors_origins()
            cors_manager.get_allowed_origins()
        
        # Measure memory after creating managers
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_per_manager = (peak_memory - initial_memory) / 100
        
        # Clean up
        del config_managers
        gc.collect()
        
        # Measure memory after cleanup
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_recovered = peak_memory - final_memory
        
        # Memory efficiency assertions
        self.assertLess(memory_per_manager, 5, "Each config manager should use less than 5MB")
        self.assertGreater(memory_recovered / (peak_memory - initial_memory), 0.8, "Should recover at least 80% of memory")
        
        print(f"\n📊 Configuration Memory Efficiency:")
        print(f"   Memory per manager: {memory_per_manager:.2f}MB")
        print(f"   Memory recovery rate: {memory_recovered / (peak_memory - initial_memory) * 100:.1f}%")


class TestWebSocketAuthenticationPerformance(unittest.TestCase):
    """Performance tests for WebSocket authentication components"""
    
    def setUp(self):
        """Set up authentication performance test environment"""
        self.config = Config()
        self.metrics = PerformanceMetrics()
        
        # Mock dependencies
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager
        )
        
        # Setup mock responses
        self.session_manager.get_session_data.return_value = {
            'user_id': 1,
            'username': 'testuser',
            'role': 'user'
        }
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_active = True
        mock_user.role = Mock()
        mock_user.role.value = 'user'
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
    
    def test_authentication_throughput(self):
        """Test authentication throughput under load"""
        self.metrics.start_measurement()
        
        # Test authentication performance
        for i in range(500):
            start_time = time.time()
            
            with patch('websocket_auth_handler.request') as mock_request:
                mock_request.headers.get.side_effect = lambda header, default=None: {
                    'X-Forwarded-For': f'192.168.1.{i % 255}',
                    'User-Agent': 'Test Client'
                }.get(header, default)
                mock_request.remote_addr = f'192.168.1.{i % 255}'
                
                result, context = self.auth_handler.authenticate_connection(
                    auth_data={'session_id': f'test-session-{i}'}
                )
            
            end_time = time.time()
            self.metrics.record_response_time(end_time - start_time)
            
            if result == AuthenticationResult.SUCCESS:
                self.metrics.record_success()
            else:
                self.metrics.record_error()
            
            # Record system metrics every 100 iterations
            if i % 100 == 0:
                self.metrics.record_memory_usage()
                self.metrics.record_cpu_usage()
        
        self.metrics.end_measurement()
        summary = self.metrics.get_summary()
        
        # Performance assertions
        self.assertLess(summary['avg_response_time_ms'], 100, "Average authentication should be under 100ms")
        self.assertGreater(summary['operations_per_second'], 10, "Should handle at least 10 authentications per second")
        self.assertGreater(summary['success_rate'], 95, "Success rate should be above 95%")
        
        print(f"\n📊 Authentication Performance:")
        print(f"   Average response time: {summary['avg_response_time_ms']:.2f}ms")
        print(f"   Operations per second: {summary['operations_per_second']:.1f}")
        print(f"   Success rate: {summary['success_rate']:.1f}%")
    
    def test_concurrent_authentication_performance(self):
        """Test concurrent authentication performance"""
        def authenticate_user(user_id: int) -> Tuple[float, bool]:
            """Authenticate a single user and return timing and success"""
            start_time = time.time()
            
            with patch('websocket_auth_handler.request') as mock_request:
                mock_request.headers.get.side_effect = lambda header, default=None: {
                    'X-Forwarded-For': f'10.0.{user_id % 255}.{user_id % 255}',
                    'User-Agent': 'Test Client'
                }.get(header, default)
                mock_request.remote_addr = f'10.0.{user_id % 255}.{user_id % 255}'
                
                result, context = self.auth_handler.authenticate_connection(
                    auth_data={'session_id': f'concurrent-session-{user_id}'}
                )
            
            end_time = time.time()
            return end_time - start_time, result == AuthenticationResult.SUCCESS
        
        # Run concurrent authentications
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(authenticate_user, i) for i in range(200)]
            
            results = []
            for future in as_completed(futures):
                try:
                    duration, success = future.result(timeout=10)
                    results.append((duration, success))
                except Exception:
                    results.append((0, False))
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        response_times = [duration for duration, success in results]
        success_count = sum(1 for duration, success in results if success)
        
        avg_response_time = statistics.mean(response_times) * 1000  # ms
        success_rate = success_count / len(results) * 100
        concurrent_throughput = len(results) / total_duration
        
        # Performance assertions
        self.assertLess(avg_response_time, 200, "Average concurrent auth should be under 200ms")
        self.assertGreater(concurrent_throughput, 5, "Should handle at least 5 concurrent auths per second")
        self.assertGreater(success_rate, 90, "Concurrent success rate should be above 90%")
        
        print(f"\n📊 Concurrent Authentication Performance:")
        print(f"   Average response time: {avg_response_time:.2f}ms")
        print(f"   Concurrent throughput: {concurrent_throughput:.1f} ops/sec")
        print(f"   Success rate: {success_rate:.1f}%")
    
    def test_rate_limiting_performance(self):
        """Test rate limiting performance under load"""
        self.metrics.start_measurement()
        
        # Test rate limiting performance
        for i in range(1000):
            start_time = time.time()
            
            # Alternate between user and IP rate limiting
            if i % 2 == 0:
                result = self.auth_handler._check_user_rate_limit(i % 100)
            else:
                result = self.auth_handler._check_ip_rate_limit(f'192.168.{i % 255}.{i % 255}')
            
            end_time = time.time()
            self.metrics.record_response_time(end_time - start_time)
            self.metrics.record_success()  # All rate limit checks are successful operations
            
            # Record system metrics every 200 iterations
            if i % 200 == 0:
                self.metrics.record_memory_usage()
                self.metrics.record_cpu_usage()
        
        self.metrics.end_measurement()
        summary = self.metrics.get_summary()
        
        # Performance assertions
        self.assertLess(summary['avg_response_time_ms'], 10, "Average rate limit check should be under 10ms")
        self.assertGreater(summary['operations_per_second'], 200, "Should handle at least 200 rate limit checks per second")
        
        print(f"\n📊 Rate Limiting Performance:")
        print(f"   Average response time: {summary['avg_response_time_ms']:.2f}ms")
        print(f"   Operations per second: {summary['operations_per_second']:.1f}")


class TestWebSocketFactoryPerformance(unittest.TestCase):
    """Performance tests for WebSocket factory components"""
    
    def setUp(self):
        """Set up factory performance test environment"""
        self.config = Config()
        self.metrics = PerformanceMetrics()
    
    def test_socketio_instance_creation_performance(self):
        """Test SocketIO instance creation performance"""
        from flask import Flask
        
        self.metrics.start_measurement()
        
        # Test SocketIO instance creation performance
        for i in range(50):  # Fewer iterations due to resource intensity
            start_time = time.time()
            
            # Create fresh components for each test
            config_manager = WebSocketConfigManager(self.config)
            cors_manager = CORSManager(config_manager)
            factory = WebSocketFactory(config_manager, cors_manager)
            
            # Create Flask app
            app = Flask(f'test_app_{i}')
            app.config['SECRET_KEY'] = f'test-secret-{i}'
            app.config['TESTING'] = True
            
            # Create SocketIO instance
            try:
                socketio = factory.create_test_socketio_instance(app)
                end_time = time.time()
                self.metrics.record_response_time(end_time - start_time)
                self.metrics.record_success()
            except Exception as e:
                end_time = time.time()
                self.metrics.record_response_time(end_time - start_time)
                self.metrics.record_error()
            
            # Record system metrics every 10 iterations
            if i % 10 == 0:
                self.metrics.record_memory_usage()
                self.metrics.record_cpu_usage()
        
        self.metrics.end_measurement()
        summary = self.metrics.get_summary()
        
        # Performance assertions
        self.assertLess(summary['avg_response_time_ms'], 1000, "Average SocketIO creation should be under 1000ms")
        self.assertGreater(summary['success_rate'], 95, "SocketIO creation success rate should be above 95%")
        
        print(f"\n📊 SocketIO Instance Creation Performance:")
        print(f"   Average response time: {summary['avg_response_time_ms']:.2f}ms")
        print(f"   Success rate: {summary['success_rate']:.1f}%")
        print(f"   Max memory usage: {summary.get('max_memory_mb', 0):.1f}MB")
    
    def test_configuration_validation_performance(self):
        """Test configuration validation performance"""
        self.metrics.start_measurement()
        
        # Test configuration validation performance
        for i in range(200):
            start_time = time.time()
            
            config_manager = WebSocketConfigManager(self.config)
            cors_manager = CORSManager(config_manager)
            factory = WebSocketFactory(config_manager, cors_manager)
            
            # Perform validation
            is_valid = factory.validate_factory_configuration()
            
            end_time = time.time()
            self.metrics.record_response_time(end_time - start_time)
            
            if is_valid:
                self.metrics.record_success()
            else:
                self.metrics.record_error()
            
            # Record system metrics every 50 iterations
            if i % 50 == 0:
                self.metrics.record_memory_usage()
                self.metrics.record_cpu_usage()
        
        self.metrics.end_measurement()
        summary = self.metrics.get_summary()
        
        # Performance assertions
        self.assertLess(summary['avg_response_time_ms'], 100, "Average validation should be under 100ms")
        self.assertGreater(summary['operations_per_second'], 10, "Should handle at least 10 validations per second")
        
        print(f"\n📊 Configuration Validation Performance:")
        print(f"   Average response time: {summary['avg_response_time_ms']:.2f}ms")
        print(f"   Operations per second: {summary['operations_per_second']:.1f}")


class TestWebSocketMemoryUsage(unittest.TestCase):
    """Memory usage tests for WebSocket components"""
    
    def setUp(self):
        """Set up memory usage test environment"""
        self.config = Config()
        gc.collect()  # Clean up before testing
    
    def test_configuration_memory_leak(self):
        """Test for memory leaks in configuration components"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and destroy many configuration managers
        for i in range(100):
            config_manager = WebSocketConfigManager(self.config)
            cors_manager = CORSManager(config_manager)
            
            # Use the managers
            config_manager.get_cors_origins()
            cors_manager.get_allowed_origins()
            config_manager.get_socketio_config()
            
            # Explicitly delete references
            del config_manager
            del cors_manager
            
            # Force garbage collection every 20 iterations
            if i % 20 == 0:
                gc.collect()
        
        # Final cleanup
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = final_memory - initial_memory
        
        # Memory leak assertion
        self.assertLess(memory_increase, 50, f"Memory increase should be less than 50MB, got {memory_increase:.1f}MB")
        
        print(f"\n📊 Configuration Memory Usage:")
        print(f"   Initial memory: {initial_memory:.1f}MB")
        print(f"   Final memory: {final_memory:.1f}MB")
        print(f"   Memory increase: {memory_increase:.1f}MB")
    
    def test_authentication_memory_usage(self):
        """Test memory usage of authentication components"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock dependencies
        db_manager = Mock(spec=DatabaseManager)
        session_manager = Mock(spec=SessionManagerV2)
        
        # Create authentication handler
        auth_handler = WebSocketAuthHandler(
            db_manager=db_manager,
            session_manager=session_manager
        )
        
        # Generate load to build up internal state
        for i in range(1000):
            # Simulate rate limiting data accumulation
            auth_handler._check_user_rate_limit(i % 100)
            auth_handler._check_ip_rate_limit(f'192.168.{i % 255}.{i % 255}')
            
            # Simulate security events
            auth_handler._log_security_event(
                'test_event', i % 100, f'session-{i}', '/',
                {'test': 'data'}
            )
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Clean up old data
        auth_handler.cleanup_old_data()
        gc.collect()
        
        cleanup_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = peak_memory - initial_memory
        memory_recovered = peak_memory - cleanup_memory
        
        # Memory usage assertions
        self.assertLess(memory_increase, 100, f"Memory increase should be less than 100MB, got {memory_increase:.1f}MB")
        self.assertGreater(memory_recovered / memory_increase, 0.5, "Should recover at least 50% of memory after cleanup")
        
        print(f"\n📊 Authentication Memory Usage:")
        print(f"   Peak memory increase: {memory_increase:.1f}MB")
        print(f"   Memory recovered: {memory_recovered:.1f}MB")
        print(f"   Recovery rate: {memory_recovered / memory_increase * 100:.1f}%")
    
    def test_sustained_load_memory_stability(self):
        """Test memory stability under sustained load"""
        process = psutil.Process()
        memory_samples = []
        
        # Mock dependencies
        db_manager = Mock(spec=DatabaseManager)
        session_manager = Mock(spec=SessionManagerV2)
        session_manager.get_session_data.return_value = {'user_id': 1}
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_active = True
        mock_user.role = Mock()
        mock_user.role.value = 'user'
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        auth_handler = WebSocketAuthHandler(db_manager=db_manager, session_manager=session_manager)
        
        # Run sustained load for 10 iterations with memory sampling
        for iteration in range(10):
            # Generate load
            for i in range(100):
                with patch('websocket_auth_handler.request') as mock_request:
                    mock_request.headers.get.return_value = 'Test Client'
                    mock_request.remote_addr = f'192.168.1.{i % 255}'
                    
                    auth_handler.authenticate_connection(
                        auth_data={'session_id': f'session-{iteration}-{i}'}
                    )
            
            # Sample memory
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_samples.append(current_memory)
            
            # Periodic cleanup
            if iteration % 3 == 0:
                auth_handler.cleanup_old_data()
                gc.collect()
        
        # Analyze memory stability
        memory_trend = memory_samples[-1] - memory_samples[0]
        memory_variance = statistics.variance(memory_samples) if len(memory_samples) > 1 else 0
        
        # Memory stability assertions
        self.assertLess(memory_trend, 50, f"Memory trend should be less than 50MB, got {memory_trend:.1f}MB")
        self.assertLess(memory_variance, 100, f"Memory variance should be low, got {memory_variance:.1f}")
        
        print(f"\n📊 Sustained Load Memory Stability:")
        print(f"   Memory trend: {memory_trend:.1f}MB")
        print(f"   Memory variance: {memory_variance:.1f}")
        print(f"   Memory samples: {[f'{m:.1f}' for m in memory_samples]}")


def run_performance_tests():
    """Run all WebSocket performance and load tests"""
    print("⚡ Running WebSocket Performance and Load Tests")
    print("=" * 55)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestWebSocketConfigurationPerformance,
        TestWebSocketAuthenticationPerformance,
        TestWebSocketFactoryPerformance,
        TestWebSocketMemoryUsage,
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 55)
    print("📊 Performance Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ All WebSocket performance tests passed!")
    else:
        print("\n❌ Some performance tests failed. Please review the output above.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_performance_tests()
    sys.exit(0 if success else 1)
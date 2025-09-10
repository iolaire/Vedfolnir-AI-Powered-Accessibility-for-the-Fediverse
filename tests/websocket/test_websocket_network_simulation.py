# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Network Condition Simulation Tests

This module provides comprehensive testing for WebSocket error recovery and
network condition simulation, including connection failures, timeout scenarios,
transport fallback testing, and resilience under adverse network conditions.
"""

import unittest
import os
import sys
import time
import threading
import random
import socket
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_auth_handler import WebSocketAuthHandler, AuthenticationResult
from websocket_factory import WebSocketFactory
from session_manager_v2 import SessionManagerV2
from app.core.database.core.database_manager import DatabaseManager


class NetworkConditionSimulator:
    """Simulator for various network conditions and failures"""
    
    def __init__(self):
        self.active_conditions = []
        self.failure_rate = 0.0
        self.latency_ms = 0
        self.packet_loss_rate = 0.0
        self.bandwidth_limit = None
    
    def simulate_connection_failure(self, failure_rate: float = 0.1):
        """Simulate random connection failures"""
        self.failure_rate = failure_rate
        self.active_conditions.append('connection_failure')
    
    def simulate_high_latency(self, latency_ms: int = 1000):
        """Simulate high network latency"""
        self.latency_ms = latency_ms
        self.active_conditions.append('high_latency')
    
    def simulate_packet_loss(self, loss_rate: float = 0.05):
        """Simulate packet loss"""
        self.packet_loss_rate = loss_rate
        self.active_conditions.append('packet_loss')
    
    def simulate_bandwidth_limit(self, bytes_per_second: int = 1024):
        """Simulate bandwidth limitations"""
        self.bandwidth_limit = bytes_per_second
        self.active_conditions.append('bandwidth_limit')
    
    def should_fail_connection(self) -> bool:
        """Check if connection should fail based on failure rate"""
        return random.random() < self.failure_rate
    
    def should_drop_packet(self) -> bool:
        """Check if packet should be dropped based on loss rate"""
        return random.random() < self.packet_loss_rate
    
    def add_latency_delay(self):
        """Add simulated latency delay"""
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000.0)
    
    def reset_conditions(self):
        """Reset all network conditions"""
        self.active_conditions = []
        self.failure_rate = 0.0
        self.latency_ms = 0
        self.packet_loss_rate = 0.0
        self.bandwidth_limit = None


class TestNetworkFailureSimulation(unittest.TestCase):
    """Test WebSocket behavior under simulated network failures"""
    
    def setUp(self):
        """Set up network failure simulation test environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        
        # Mock dependencies
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager
        )
        
        self.network_simulator = NetworkConditionSimulator()
    
    def tearDown(self):
        """Clean up after network failure tests"""
        self.network_simulator.reset_conditions()
    
    def test_connection_timeout_simulation(self):
        """Test behavior during connection timeouts"""
        # Simulate connection timeout by making session manager slow
        def slow_session_response(*args, **kwargs):
            time.sleep(2)  # 2 second delay
            return {'user_id': 1, 'username': 'testuser'}
        
        self.session_manager.get_session_data.side_effect = slow_session_response
        
        # Mock user for successful authentication after delay
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_active = True
        mock_user.role = Mock()
        mock_user.role.value = 'user'
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Test authentication with timeout
        start_time = time.time()
        
        with patch('websocket_auth_handler.request') as mock_request:
            mock_request.headers.get.return_value = 'Test Client'
            mock_request.remote_addr = '127.0.0.1'
            
            result, context = self.auth_handler.authenticate_connection(
                auth_data={'session_id': 'test-session'}
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete despite delay
        self.assertGreaterEqual(duration, 2.0)  # Should take at least 2 seconds
        self.assertEqual(result, AuthenticationResult.SUCCESS)
    
    def test_intermittent_connection_failures(self):
        """Test handling of intermittent connection failures"""
        self.network_simulator.simulate_connection_failure(failure_rate=0.3)
        
        # Simulate intermittent failures in session manager
        def intermittent_failure(*args, **kwargs):
            if self.network_simulator.should_fail_connection():
                raise ConnectionError("Simulated network failure")
            return {'user_id': 1, 'username': 'testuser'}
        
        self.session_manager.get_session_data.side_effect = intermittent_failure
        
        # Test multiple authentication attempts
        success_count = 0
        failure_count = 0
        
        for i in range(20):
            with patch('websocket_auth_handler.request') as mock_request:
                mock_request.headers.get.return_value = 'Test Client'
                mock_request.remote_addr = '127.0.0.1'
                
                try:
                    result, context = self.auth_handler.authenticate_connection(
                        auth_data={'session_id': f'test-session-{i}'}
                    )
                    
                    if result == AuthenticationResult.SUCCESS:
                        success_count += 1
                    else:
                        failure_count += 1
                        
                except Exception:
                    failure_count += 1
        
        # Should have some successes and some failures
        self.assertGreater(success_count, 0)
        self.assertGreater(failure_count, 0)
        
        # Failure rate should be approximately what we set (with some variance)
        actual_failure_rate = failure_count / (success_count + failure_count)
        self.assertLess(abs(actual_failure_rate - 0.3), 0.2)  # Within 20% of expected
    
    def test_database_connection_loss(self):
        """Test behavior when database connection is lost"""
        # Simulate database connection loss
        self.db_manager.get_session.side_effect = Exception("Database connection lost")
        
        # Session manager still works
        self.session_manager.get_session_data.return_value = {
            'user_id': 1, 'username': 'testuser'
        }
        
        # Test authentication with database failure
        with patch('websocket_auth_handler.request') as mock_request:
            mock_request.headers.get.return_value = 'Test Client'
            mock_request.remote_addr = '127.0.0.1'
            
            result, context = self.auth_handler.authenticate_connection(
                auth_data={'session_id': 'test-session'}
            )
        
        # Should fail gracefully
        self.assertEqual(result, AuthenticationResult.SYSTEM_ERROR)
        self.assertIsNone(context)
    
    def test_redis_session_failure(self):
        """Test behavior when Redis session storage fails"""
        # Simulate Redis failure
        self.session_manager.get_session_data.side_effect = Exception("Redis connection failed")
        
        # Test authentication with Redis failure
        with patch('websocket_auth_handler.request') as mock_request:
            mock_request.headers.get.return_value = 'Test Client'
            mock_request.remote_addr = '127.0.0.1'
            
            result, context = self.auth_handler.authenticate_connection(
                auth_data={'session_id': 'test-session'}
            )
        
        # Should fail with invalid session
        self.assertEqual(result, AuthenticationResult.INVALID_SESSION)
        self.assertIsNone(context)
    
    def test_partial_service_degradation(self):
        """Test behavior during partial service degradation"""
        # Simulate slow but working services
        def slow_session_manager(*args, **kwargs):
            time.sleep(0.5)  # 500ms delay
            return {'user_id': 1, 'username': 'testuser'}
        
        def slow_database(*args, **kwargs):
            time.sleep(0.3)  # 300ms delay
            mock_user = Mock()
            mock_user.id = 1
            mock_user.is_active = True
            mock_user.role = Mock()
            mock_user.role.value = 'user'
            
            mock_db_session = Mock()
            mock_db_session.get.return_value = mock_user
            return mock_db_session
        
        self.session_manager.get_session_data.side_effect = slow_session_manager
        self.db_manager.get_session.return_value.__enter__.side_effect = slow_database
        
        # Test authentication with degraded performance
        start_time = time.time()
        
        with patch('websocket_auth_handler.request') as mock_request:
            mock_request.headers.get.return_value = 'Test Client'
            mock_request.remote_addr = '127.0.0.1'
            
            result, context = self.auth_handler.authenticate_connection(
                auth_data={'session_id': 'test-session'}
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete but take longer
        self.assertGreaterEqual(duration, 0.8)  # Should take at least 800ms
        self.assertEqual(result, AuthenticationResult.SUCCESS)


class TestTransportFallbackScenarios(unittest.TestCase):
    """Test transport fallback scenarios under network conditions"""
    
    def setUp(self):
        """Set up transport fallback test environment"""
        self.config = Config()
        self.original_env = {}
        
        # Store original environment
        env_vars = ['SOCKETIO_TRANSPORTS']
        for var in env_vars:
            self.original_env[var] = os.getenv(var)
    
    def tearDown(self):
        """Clean up transport fallback test environment"""
        # Restore original environment
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_websocket_to_polling_fallback(self):
        """Test fallback from WebSocket to polling transport"""
        # Configure WebSocket first, then polling
        os.environ['SOCKETIO_TRANSPORTS'] = 'websocket,polling'
        
        config_manager = WebSocketConfigManager(self.config)
        socketio_config = config_manager.get_socketio_config()
        
        # Should have both transports with WebSocket first
        self.assertEqual(socketio_config['transports'], ['websocket', 'polling'])
        
        # Simulate WebSocket failure by configuring polling only
        os.environ['SOCKETIO_TRANSPORTS'] = 'polling'
        
        config_manager = WebSocketConfigManager(self.config)
        socketio_config = config_manager.get_socketio_config()
        
        # Should fall back to polling only
        self.assertEqual(socketio_config['transports'], ['polling'])
    
    def test_polling_only_configuration(self):
        """Test polling-only configuration for restricted networks"""
        os.environ['SOCKETIO_TRANSPORTS'] = 'polling'
        
        config_manager = WebSocketConfigManager(self.config)
        socketio_config = config_manager.get_socketio_config()
        
        # Should use polling only
        self.assertEqual(socketio_config['transports'], ['polling'])
        
        # Client configuration should also reflect this
        client_config = config_manager.get_client_config()
        self.assertEqual(client_config['transports'], ['polling'])
    
    def test_invalid_transport_handling(self):
        """Test handling of invalid transport configurations"""
        # Configure invalid transport
        os.environ['SOCKETIO_TRANSPORTS'] = 'invalid_transport,websocket'
        
        config_manager = WebSocketConfigManager(self.config)
        socketio_config = config_manager.get_socketio_config()
        
        # Should filter out invalid transport
        self.assertNotIn('invalid_transport', socketio_config['transports'])
        self.assertIn('websocket', socketio_config['transports'])
    
    def test_empty_transport_configuration(self):
        """Test handling of empty transport configuration"""
        os.environ['SOCKETIO_TRANSPORTS'] = ''
        
        config_manager = WebSocketConfigManager(self.config)
        socketio_config = config_manager.get_socketio_config()
        
        # Should fall back to default transports
        self.assertTrue(len(socketio_config['transports']) > 0)
        self.assertIn('websocket', socketio_config['transports'])
        self.assertIn('polling', socketio_config['transports'])
    
    def test_transport_priority_ordering(self):
        """Test transport priority ordering"""
        transport_orders = [
            'websocket,polling',
            'polling,websocket',
            'websocket',
            'polling'
        ]
        
        for transport_order in transport_orders:
            with self.subTest(transport_order=transport_order):
                os.environ['SOCKETIO_TRANSPORTS'] = transport_order
                
                config_manager = WebSocketConfigManager(self.config)
                socketio_config = config_manager.get_socketio_config()
                
                expected_transports = transport_order.split(',')
                self.assertEqual(socketio_config['transports'], expected_transports)


class TestConnectionResilienceScenarios(unittest.TestCase):
    """Test connection resilience under various network scenarios"""
    
    def setUp(self):
        """Set up connection resilience test environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        
        # Mock dependencies
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager,
            rate_limit_window=60,  # 1 minute for testing
            max_attempts_per_window=10,
            max_attempts_per_ip=50
        )
    
    def test_rate_limiting_under_attack(self):
        """Test rate limiting behavior under simulated attack"""
        attacker_ip = '192.168.1.100'
        
        # Simulate rapid connection attempts from single IP
        for i in range(60):  # Exceed IP rate limit
            result = self.auth_handler._check_ip_rate_limit(attacker_ip)
            
            if i < 50:  # First 50 should be allowed
                self.assertTrue(result, f"Attempt {i+1} should be allowed")
            else:  # Remaining should be blocked
                self.assertFalse(result, f"Attempt {i+1} should be blocked")
    
    def test_distributed_attack_simulation(self):
        """Test behavior under distributed attack simulation"""
        # Simulate attacks from multiple IPs
        attack_ips = [f'192.168.1.{i}' for i in range(1, 21)]  # 20 different IPs
        
        # Each IP makes many requests
        blocked_ips = 0
        
        for ip in attack_ips:
            # Make requests until blocked
            for attempt in range(60):
                result = self.auth_handler._check_ip_rate_limit(ip)
                if not result:
                    blocked_ips += 1
                    break
        
        # Should block most attacking IPs
        self.assertGreater(blocked_ips, 15)  # At least 75% should be blocked
    
    def test_legitimate_traffic_during_attack(self):
        """Test that legitimate traffic works during attack"""
        attacker_ip = '192.168.1.100'
        legitimate_ip = '10.0.0.1'
        
        # Exhaust rate limit for attacker
        for i in range(60):
            self.auth_handler._check_ip_rate_limit(attacker_ip)
        
        # Legitimate traffic should still work
        for i in range(10):
            result = self.auth_handler._check_ip_rate_limit(legitimate_ip)
            self.assertTrue(result, f"Legitimate request {i+1} should be allowed")
    
    def test_user_rate_limiting_fairness(self):
        """Test user rate limiting fairness"""
        # Test multiple users
        user_ids = list(range(1, 11))  # 10 users
        
        # Each user makes requests
        for user_id in user_ids:
            for attempt in range(8):  # Under the limit of 10
                result = self.auth_handler._check_user_rate_limit(user_id)
                self.assertTrue(result, f"User {user_id} attempt {attempt+1} should be allowed")
        
        # One user exceeds limit
        for attempt in range(5):  # 5 more attempts for user 1 (total 13)
            result = self.auth_handler._check_user_rate_limit(1)
            if attempt < 2:  # First 2 more should be allowed (total 10)
                self.assertTrue(result)
            else:  # Remaining should be blocked
                self.assertFalse(result)
        
        # Other users should still work
        for user_id in range(2, 11):
            result = self.auth_handler._check_user_rate_limit(user_id)
            self.assertTrue(result, f"User {user_id} should still be allowed")
    
    def test_recovery_after_rate_limiting(self):
        """Test recovery after rate limiting period"""
        user_id = 1
        
        # Exhaust rate limit
        for i in range(15):
            self.auth_handler._check_user_rate_limit(user_id)
        
        # Should be rate limited
        result = self.auth_handler._check_user_rate_limit(user_id)
        self.assertFalse(result)
        
        # Simulate time passing by manipulating the rate limiter's internal state
        # Clear old attempts to simulate time window expiration
        self.auth_handler._user_attempts[user_id].clear()
        
        # Should be able to make requests again
        result = self.auth_handler._check_user_rate_limit(user_id)
        self.assertTrue(result)
    
    def test_concurrent_authentication_resilience(self):
        """Test authentication resilience under concurrent load"""
        # Mock successful authentication setup
        self.session_manager.get_session_data.return_value = {
            'user_id': 1, 'username': 'testuser'
        }
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_active = True
        mock_user.role = Mock()
        mock_user.role.value = 'user'
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        def authenticate_user(user_id):
            """Authenticate a single user"""
            with patch('websocket_auth_handler.request') as mock_request:
                mock_request.headers.get.return_value = 'Test Client'
                mock_request.remote_addr = f'192.168.1.{user_id % 255}'
                
                return self.auth_handler.authenticate_connection(
                    auth_data={'session_id': f'session-{user_id}'}
                )
        
        # Run concurrent authentications
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(authenticate_user, i) for i in range(100)]
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                except Exception as e:
                    results.append((AuthenticationResult.SYSTEM_ERROR, None))
        
        # Should handle all requests
        self.assertEqual(len(results), 100)
        
        # Most should succeed (some might be rate limited)
        success_count = sum(1 for result, context in results if result == AuthenticationResult.SUCCESS)
        self.assertGreater(success_count, 80)  # At least 80% should succeed


class TestNetworkLatencySimulation(unittest.TestCase):
    """Test WebSocket behavior under high network latency"""
    
    def setUp(self):
        """Set up network latency simulation test environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        
        # Mock dependencies with latency simulation
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager
        )
    
    def test_high_latency_authentication(self):
        """Test authentication under high network latency"""
        # Simulate high latency in session manager
        def high_latency_session(*args, **kwargs):
            time.sleep(1.0)  # 1 second latency
            return {'user_id': 1, 'username': 'testuser'}
        
        # Simulate high latency in database
        def high_latency_database(*args, **kwargs):
            time.sleep(0.8)  # 800ms latency
            mock_user = Mock()
            mock_user.id = 1
            mock_user.is_active = True
            mock_user.role = Mock()
            mock_user.role.value = 'user'
            
            mock_db_session = Mock()
            mock_db_session.get.return_value = mock_user
            return mock_db_session
        
        self.session_manager.get_session_data.side_effect = high_latency_session
        self.db_manager.get_session.return_value.__enter__.side_effect = high_latency_database
        
        # Test authentication with high latency
        start_time = time.time()
        
        with patch('websocket_auth_handler.request') as mock_request:
            mock_request.headers.get.return_value = 'Test Client'
            mock_request.remote_addr = '127.0.0.1'
            
            result, context = self.auth_handler.authenticate_connection(
                auth_data={'session_id': 'test-session'}
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete despite high latency
        self.assertGreaterEqual(duration, 1.8)  # Should take at least 1.8 seconds
        self.assertEqual(result, AuthenticationResult.SUCCESS)
    
    def test_timeout_configuration_effectiveness(self):
        """Test that timeout configurations are effective"""
        # Test different timeout configurations
        timeout_configs = [
            {'ping_timeout': 30, 'ping_interval': 10},
            {'ping_timeout': 60, 'ping_interval': 25},
            {'ping_timeout': 120, 'ping_interval': 30},
        ]
        
        for timeout_config in timeout_configs:
            with self.subTest(timeout_config=timeout_config):
                # Set timeout environment variables
                for key, value in timeout_config.items():
                    env_key = f'SOCKETIO_{key.upper()}'
                    os.environ[env_key] = str(value)
                
                try:
                    config_manager = WebSocketConfigManager(self.config)
                    socketio_config = config_manager.get_socketio_config()
                    
                    # Verify timeout configuration was applied
                    self.assertEqual(socketio_config['ping_timeout'], timeout_config['ping_timeout'])
                    self.assertEqual(socketio_config['ping_interval'], timeout_config['ping_interval'])
                    
                    # Verify ping_interval < ping_timeout
                    self.assertLess(socketio_config['ping_interval'], socketio_config['ping_timeout'])
                    
                finally:
                    # Clean up environment variables
                    for key in timeout_config.keys():
                        env_key = f'SOCKETIO_{key.upper()}'
                        if env_key in os.environ:
                            del os.environ[env_key]
    
    def test_variable_latency_handling(self):
        """Test handling of variable network latency"""
        latencies = [0.1, 0.5, 1.0, 0.2, 2.0, 0.3, 1.5, 0.1]  # Variable latencies
        
        def variable_latency_session(*args, **kwargs):
            latency = latencies[len(self.session_manager.get_session_data.call_args_list) % len(latencies)]
            time.sleep(latency)
            return {'user_id': 1, 'username': 'testuser'}
        
        self.session_manager.get_session_data.side_effect = variable_latency_session
        
        # Mock database
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_active = True
        mock_user.role = Mock()
        mock_user.role.value = 'user'
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Test multiple authentications with variable latency
        durations = []
        
        for i in range(len(latencies)):
            start_time = time.time()
            
            with patch('websocket_auth_handler.request') as mock_request:
                mock_request.headers.get.return_value = 'Test Client'
                mock_request.remote_addr = '127.0.0.1'
                
                result, context = self.auth_handler.authenticate_connection(
                    auth_data={'session_id': f'test-session-{i}'}
                )
            
            end_time = time.time()
            duration = end_time - start_time
            durations.append(duration)
            
            # Should succeed despite variable latency
            self.assertEqual(result, AuthenticationResult.SUCCESS)
        
        # Verify that durations roughly correspond to latencies
        for i, expected_latency in enumerate(latencies):
            self.assertGreaterEqual(durations[i], expected_latency * 0.8)  # Allow some variance


def run_network_simulation_tests():
    """Run all WebSocket network simulation tests"""
    print("🌐 Running WebSocket Network Condition Simulation Tests")
    print("=" * 65)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestNetworkFailureSimulation,
        TestTransportFallbackScenarios,
        TestConnectionResilienceScenarios,
        TestNetworkLatencySimulation,
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 65)
    print("📊 Network Simulation Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ All WebSocket network simulation tests passed!")
    else:
        print("\n❌ Some network simulation tests failed. Please review the output above.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_network_simulation_tests()
    sys.exit(0 if success else 1)
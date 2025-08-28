# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive WebSocket CORS Standardization Test Suite

This module provides comprehensive testing for the WebSocket CORS standardization system,
including unit tests for configuration manager, CORS manager, authentication handler,
integration tests for end-to-end WebSocket connection scenarios, CORS-specific testing
with multiple origin configurations, error recovery testing with simulated network
conditions, and performance tests for connection load and message throughput.
"""

import unittest
import os
import sys
import time
import threading
import json
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager
from models import User, UserRole
from websocket_config_manager import WebSocketConfigManager, WebSocketConfig
from websocket_cors_manager import CORSManager
from websocket_auth_handler import WebSocketAuthHandler, AuthenticationResult, AuthenticationContext
from websocket_factory import WebSocketFactory
from session_manager_v2 import SessionManagerV2
from redis_session_backend import RedisSessionBackend


class TestWebSocketConfigManager(unittest.TestCase):
    """Unit tests for WebSocket Configuration Manager"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        
        # Store original environment variables
        self.original_env = {}
        env_vars = [
            'FLASK_HOST', 'FLASK_PORT', 'SOCKETIO_CORS_ORIGINS',
            'SOCKETIO_TRANSPORTS', 'SOCKETIO_PING_TIMEOUT',
            'SOCKETIO_PING_INTERVAL', 'SOCKETIO_RECONNECTION_ATTEMPTS'
        ]
        for var in env_vars:
            self.original_env[var] = os.getenv(var)
    
    def tearDown(self):
        """Clean up test environment"""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_default_configuration_loading(self):
        """Test loading default configuration"""
        config_manager = WebSocketConfigManager(self.config)
        
        # Test that configuration is loaded
        self.assertIsNotNone(config_manager._websocket_config)
        
        # Test default values
        cors_origins = config_manager.get_cors_origins()
        self.assertIsInstance(cors_origins, list)
        self.assertTrue(len(cors_origins) > 0)
        
        # Test SocketIO configuration
        socketio_config = config_manager.get_socketio_config()
        self.assertIsInstance(socketio_config, dict)
        self.assertIn('cors_allowed_origins', socketio_config)
        self.assertIn('async_mode', socketio_config)
        self.assertIn('transports', socketio_config)
    
    def test_environment_variable_parsing(self):
        """Test parsing of environment variables"""
        # Set test environment variables
        os.environ['FLASK_HOST'] = 'testhost.example.com'
        os.environ['FLASK_PORT'] = '8080'
        os.environ['SOCKETIO_PING_TIMEOUT'] = '120'
        os.environ['SOCKETIO_PING_INTERVAL'] = '30'
        os.environ['SOCKETIO_TRANSPORTS'] = 'websocket,polling'
        
        # Create new config manager to pick up environment changes
        config_manager = WebSocketConfigManager(self.config)
        
        # Test CORS origins generation
        cors_origins = config_manager.get_cors_origins()
        self.assertIn('http://testhost.example.com:8080', cors_origins)
        self.assertIn('https://testhost.example.com:8080', cors_origins)
        
        # Test SocketIO configuration
        socketio_config = config_manager.get_socketio_config()
        self.assertEqual(socketio_config['ping_timeout'], 120)
        self.assertEqual(socketio_config['ping_interval'], 30)
        self.assertEqual(socketio_config['transports'], ['websocket', 'polling'])
    
    def test_explicit_cors_origins(self):
        """Test explicit CORS origins configuration"""
        # Test wildcard
        os.environ['SOCKETIO_CORS_ORIGINS'] = '*'
        config_manager = WebSocketConfigManager(self.config)
        cors_origins = config_manager.get_cors_origins()
        self.assertEqual(cors_origins, ['*'])
        
        # Test specific origins
        os.environ['SOCKETIO_CORS_ORIGINS'] = 'https://example.com,https://test.com'
        config_manager = WebSocketConfigManager(self.config)
        cors_origins = config_manager.get_cors_origins()
        self.assertIn('https://example.com', cors_origins)
        self.assertIn('https://test.com', cors_origins)
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        # Test valid configuration
        self.assertTrue(self.config_manager.validate_configuration())
        
        # Test invalid configuration
        os.environ['SOCKETIO_PING_TIMEOUT'] = '-1'
        config_manager = WebSocketConfigManager(self.config)
        self.assertFalse(config_manager.validate_configuration())
        
        errors = config_manager.get_validation_errors()
        self.assertTrue(any('ping_timeout must be positive' in error for error in errors))
    
    def test_fallback_configuration(self):
        """Test fallback configuration when errors occur"""
        # Mock an error in configuration loading
        with patch.object(WebSocketConfigManager, '_create_websocket_config', side_effect=Exception("Test error")):
            config_manager = WebSocketConfigManager(self.config)
            
            # Should have fallback configuration
            self.assertIsNotNone(config_manager._websocket_config)
            
            # Should have validation errors
            errors = config_manager.get_validation_errors()
            self.assertTrue(len(errors) > 0)
            self.assertTrue(any('fallback configuration' in error for error in errors))
    
    def test_client_configuration(self):
        """Test client configuration generation"""
        client_config = self.config_manager.get_client_config()
        
        self.assertIsInstance(client_config, dict)
        self.assertIn('url', client_config)
        self.assertIn('transports', client_config)
        self.assertIn('reconnection', client_config)
        self.assertIn('reconnectionAttempts', client_config)
        self.assertIn('timeout', client_config)
    
    def test_configuration_reload(self):
        """Test configuration reloading"""
        # Get initial configuration
        initial_origins = self.config_manager.get_cors_origins()
        
        # Change environment
        os.environ['FLASK_HOST'] = 'newhost.example.com'
        
        # Reload configuration
        self.config_manager.reload_configuration()
        
        # Check that configuration changed
        new_origins = self.config_manager.get_cors_origins()
        self.assertNotEqual(initial_origins, new_origins)
        self.assertTrue(any('newhost.example.com' in origin for origin in new_origins))


class TestCORSManager(unittest.TestCase):
    """Unit tests for CORS Manager"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        
        # Store original environment variables
        self.original_env = {}
        env_vars = ['FLASK_HOST', 'FLASK_PORT', 'FLASK_ENV']
        for var in env_vars:
            self.original_env[var] = os.getenv(var)
    
    def tearDown(self):
        """Clean up test environment"""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_allowed_origins_calculation(self):
        """Test calculation of allowed origins"""
        allowed_origins = self.cors_manager.get_allowed_origins()
        
        self.assertIsInstance(allowed_origins, list)
        self.assertTrue(len(allowed_origins) > 0)
        
        # Should include localhost variants
        localhost_origins = [origin for origin in allowed_origins if 'localhost' in origin or '127.0.0.1' in origin]
        self.assertTrue(len(localhost_origins) > 0)
    
    def test_origin_validation(self):
        """Test origin validation"""
        # Test valid origins
        valid_origins = [
            'http://localhost:5000',
            'https://127.0.0.1:5000',
            'http://localhost:3000',
        ]
        
        for origin in valid_origins:
            with self.subTest(origin=origin):
                self.assertTrue(self.cors_manager.validate_origin(origin))
        
        # Test invalid origins
        invalid_origins = [
            'http://malicious.com',
            'https://evil.example.com',
            'ftp://localhost:5000',
            'invalid-url',
            '',
        ]
        
        for origin in invalid_origins:
            with self.subTest(origin=origin):
                self.assertFalse(self.cors_manager.validate_origin(origin))
    
    def test_localhost_variants(self):
        """Test localhost/127.0.0.1 variant handling"""
        # Set localhost as host
        os.environ['FLASK_HOST'] = 'localhost'
        os.environ['FLASK_PORT'] = '5000'
        
        cors_manager = CORSManager(WebSocketConfigManager(self.config))
        allowed_origins = cors_manager.get_allowed_origins()
        
        # Should include both localhost and 127.0.0.1 variants
        localhost_found = any('localhost:5000' in origin for origin in allowed_origins)
        ip_found = any('127.0.0.1:5000' in origin for origin in allowed_origins)
        
        self.assertTrue(localhost_found)
        self.assertTrue(ip_found)
    
    def test_protocol_variants(self):
        """Test HTTP/HTTPS protocol variant generation"""
        allowed_origins = self.cors_manager.get_allowed_origins()
        
        # Should include both HTTP and HTTPS variants
        http_origins = [origin for origin in allowed_origins if origin.startswith('http://')]
        https_origins = [origin for origin in allowed_origins if origin.startswith('https://')]
        
        self.assertTrue(len(http_origins) > 0)
        self.assertTrue(len(https_origins) > 0)
    
    def test_development_environment_origins(self):
        """Test development environment specific origins"""
        os.environ['FLASK_ENV'] = 'development'
        
        cors_manager = CORSManager(WebSocketConfigManager(self.config))
        allowed_origins = cors_manager.get_allowed_origins()
        
        # Should include common development ports
        dev_ports = ['3000', '8080', '4200', '8000']
        for port in dev_ports:
            with self.subTest(port=port):
                port_found = any(f':{port}' in origin for origin in allowed_origins)
                self.assertTrue(port_found, f"Port {port} not found in origins")
    
    def test_websocket_origin_validation(self):
        """Test WebSocket-specific origin validation"""
        # Test valid WebSocket origin
        is_valid, error_msg = self.cors_manager.validate_websocket_origin('http://localhost:5000')
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "Origin validated successfully")
        
        # Test invalid WebSocket origin
        is_valid, error_msg = self.cors_manager.validate_websocket_origin('http://malicious.com')
        self.assertFalse(is_valid)
        self.assertIn('not in allowed origins', error_msg)
        
        # Test missing origin
        is_valid, error_msg = self.cors_manager.validate_websocket_origin('')
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "No origin header provided")
    
    def test_cors_cache_management(self):
        """Test CORS origins cache management"""
        # Get initial origins
        initial_origins = self.cors_manager.get_allowed_origins()
        
        # Clear cache
        self.cors_manager.clear_cache()
        
        # Get origins again (should recalculate)
        new_origins = self.cors_manager.get_allowed_origins()
        
        # Should be the same (unless environment changed)
        self.assertEqual(initial_origins, new_origins)
    
    def test_cors_debug_info(self):
        """Test CORS debug information"""
        debug_info = self.cors_manager.get_cors_debug_info()
        
        self.assertIsInstance(debug_info, dict)
        self.assertIn('allowed_origins', debug_info)
        self.assertIn('origin_patterns', debug_info)
        self.assertIn('environment', debug_info)


class TestWebSocketAuthHandler(unittest.TestCase):
    """Unit tests for WebSocket Authentication Handler"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager,
            rate_limit_window=60,  # 1 minute for testing
            max_attempts_per_window=5,
            max_attempts_per_ip=20
        )
    
    def test_authentication_context_creation(self):
        """Test authentication context creation"""
        context = AuthenticationContext(
            user_id=1,
            username='testuser',
            email='test@example.com',
            role=UserRole.ADMIN,
            session_id='test-session-123',
            platform_connection_id=1,
            platform_name='Test Platform',
            platform_type='mastodon'
        )
        
        self.assertEqual(context.user_id, 1)
        self.assertEqual(context.username, 'testuser')
        self.assertTrue(context.is_admin)
        self.assertIn('system_management', context.permissions)
    
    def test_session_validation(self):
        """Test session validation"""
        # Mock session data
        session_data = {
            'user_id': 1,
            'username': 'testuser',
            'role': 'admin'
        }
        self.session_manager.get_session_data.return_value = session_data
        
        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_active = True
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Test validation
        is_valid = self.auth_handler.validate_user_session(1, 'test-session-123')
        self.assertTrue(is_valid)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        user_id = 1
        
        # Test within rate limit
        for i in range(4):  # 4 attempts (under limit of 5)
            result = self.auth_handler._check_user_rate_limit(user_id)
            self.assertTrue(result, f"Attempt {i+1} should be allowed")
        
        # Test rate limit exceeded
        result = self.auth_handler._check_user_rate_limit(user_id)
        self.assertFalse(result, "5th attempt should be rate limited")
    
    def test_ip_rate_limiting(self):
        """Test IP-based rate limiting"""
        ip_address = '192.168.1.100'
        
        # Test within rate limit
        for i in range(19):  # 19 attempts (under limit of 20)
            result = self.auth_handler._check_ip_rate_limit(ip_address)
            self.assertTrue(result, f"IP attempt {i+1} should be allowed")
        
        # Test rate limit exceeded
        result = self.auth_handler._check_ip_rate_limit(ip_address)
        self.assertFalse(result, "20th IP attempt should be rate limited")
    
    def test_admin_authorization(self):
        """Test admin authorization"""
        # Create admin context
        admin_context = AuthenticationContext(
            user_id=1,
            username='admin',
            email='admin@example.com',
            role=UserRole.ADMIN,
            session_id='admin-session-123'
        )
        
        # Test admin access
        self.assertTrue(self.auth_handler.authorize_admin_access(admin_context))
        self.assertTrue(self.auth_handler.authorize_admin_access(admin_context, 'system_management'))
        
        # Create non-admin context
        user_context = AuthenticationContext(
            user_id=2,
            username='user',
            email='user@example.com',
            role=UserRole.VIEWER,
            session_id='user-session-123'
        )
        
        # Test non-admin access denied
        self.assertFalse(self.auth_handler.authorize_admin_access(user_context))
    
    def test_authentication_stats(self):
        """Test authentication statistics"""
        # Generate some test data
        self.auth_handler._check_user_rate_limit(1)
        self.auth_handler._check_user_rate_limit(2)
        self.auth_handler._check_ip_rate_limit('192.168.1.1')
        
        stats = self.auth_handler.get_authentication_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('rate_limit_window_seconds', stats)
        self.assertIn('active_users_in_window', stats)
        self.assertIn('active_ips_in_window', stats)
        self.assertIn('security_events_in_window', stats)
    
    def test_cleanup_old_data(self):
        """Test cleanup of old rate limiting data"""
        # Add some test data
        self.auth_handler._check_user_rate_limit(1)
        self.auth_handler._check_ip_rate_limit('192.168.1.1')
        
        # Verify data exists
        self.assertTrue(len(self.auth_handler._user_attempts) > 0)
        self.assertTrue(len(self.auth_handler._ip_attempts) > 0)
        
        # Run cleanup
        self.auth_handler.cleanup_old_data()
        
        # Data should still exist (not old enough)
        self.assertTrue(len(self.auth_handler._user_attempts) > 0)
        self.assertTrue(len(self.auth_handler._ip_attempts) > 0)


class TestWebSocketFactory(unittest.TestCase):
    """Unit tests for WebSocket Factory"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        self.factory = WebSocketFactory(self.config_manager, self.cors_manager)
    
    def test_factory_initialization(self):
        """Test factory initialization"""
        self.assertIsNotNone(self.factory.config_manager)
        self.assertIsNotNone(self.factory.cors_manager)
        self.assertEqual(len(self.factory._error_handlers), 0)
        self.assertEqual(len(self.factory._middleware_functions), 0)
    
    def test_unified_socketio_config(self):
        """Test unified SocketIO configuration"""
        config = self.factory._get_unified_socketio_config()
        
        self.assertIsInstance(config, dict)
        self.assertIn('cors_allowed_origins', config)
        self.assertIn('cors_credentials', config)
        self.assertIn('async_mode', config)
        self.assertIn('transports', config)
        self.assertIn('logger', config)
    
    def test_middleware_registration(self):
        """Test middleware registration"""
        def test_middleware(socketio):
            pass
        
        self.factory.register_middleware(test_middleware)
        self.assertEqual(len(self.factory._middleware_functions), 1)
    
    def test_error_handler_registration(self):
        """Test error handler registration"""
        def test_error_handler(error):
            pass
        
        self.factory.register_error_handler('test_error', test_error_handler)
        self.assertIn('test_error', self.factory._error_handlers)
    
    def test_factory_status(self):
        """Test factory status information"""
        status = self.factory.get_factory_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('config_manager_status', status)
        self.assertIn('cors_debug_info', status)
        self.assertIn('registered_middleware', status)
        self.assertIn('registered_error_handlers', status)
    
    def test_configuration_validation(self):
        """Test factory configuration validation"""
        is_valid = self.factory.validate_factory_configuration()
        self.assertTrue(is_valid)


class TestWebSocketIntegration(unittest.TestCase):
    """Integration tests for end-to-end WebSocket connection scenarios"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        self.factory = WebSocketFactory(self.config_manager, self.cors_manager)
        
        # Mock Flask app
        self.app = Mock()
        self.app.logger = Mock()
    
    def test_end_to_end_configuration_flow(self):
        """Test complete configuration flow from environment to SocketIO"""
        # Set test environment
        os.environ['FLASK_HOST'] = 'testhost.local'
        os.environ['FLASK_PORT'] = '9000'
        os.environ['SOCKETIO_TRANSPORTS'] = 'websocket'
        
        try:
            # Create new managers with test environment
            config_manager = WebSocketConfigManager(self.config)
            cors_manager = CORSManager(config_manager)
            factory = WebSocketFactory(config_manager, cors_manager)
            
            # Test configuration propagation
            cors_origins = cors_manager.get_allowed_origins()
            self.assertTrue(any('testhost.local:9000' in origin for origin in cors_origins))
            
            # Test SocketIO configuration
            socketio_config = factory._get_unified_socketio_config()
            self.assertIn('http://testhost.local:9000', socketio_config['cors_allowed_origins'])
            self.assertEqual(socketio_config['transports'], ['websocket'])
            
        finally:
            # Clean up environment
            if 'FLASK_HOST' in os.environ:
                del os.environ['FLASK_HOST']
            if 'FLASK_PORT' in os.environ:
                del os.environ['FLASK_PORT']
            if 'SOCKETIO_TRANSPORTS' in os.environ:
                del os.environ['SOCKETIO_TRANSPORTS']
    
    def test_cors_validation_integration(self):
        """Test CORS validation integration across components"""
        # Test valid origin validation
        test_origin = 'http://localhost:5000'
        
        # Should be valid in CORS manager
        self.assertTrue(self.cors_manager.validate_origin(test_origin))
        
        # Should be valid for WebSocket connections
        is_valid, error_msg = self.cors_manager.validate_websocket_origin(test_origin)
        self.assertTrue(is_valid)
        
        # Should be included in allowed origins
        allowed_origins = self.cors_manager.get_allowed_origins()
        self.assertIn(test_origin, allowed_origins)
    
    def test_configuration_error_handling(self):
        """Test error handling across configuration components"""
        # Test with invalid configuration
        with patch.dict(os.environ, {'SOCKETIO_PING_TIMEOUT': 'invalid'}):
            try:
                config_manager = WebSocketConfigManager(self.config)
                
                # Should handle error gracefully
                self.assertIsNotNone(config_manager._websocket_config)
                
                # Should have validation errors
                errors = config_manager.get_validation_errors()
                self.assertTrue(len(errors) > 0)
                
            except Exception as e:
                self.fail(f"Configuration should handle errors gracefully: {e}")


class TestCORSMultipleOrigins(unittest.TestCase):
    """CORS-specific testing with multiple origin configurations"""
    
    def setUp(self):
        """Set up CORS testing environment"""
        self.config = Config()
        self.original_env = {}
        
        # Store original environment
        env_vars = ['FLASK_HOST', 'FLASK_PORT', 'FLASK_ENV', 'SOCKETIO_CORS_ORIGINS']
        for var in env_vars:
            self.original_env[var] = os.getenv(var)
    
    def tearDown(self):
        """Clean up CORS testing environment"""
        # Restore original environment
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_multiple_explicit_origins(self):
        """Test multiple explicit CORS origins"""
        origins = 'https://app1.example.com,https://app2.example.com,http://localhost:3000'
        os.environ['SOCKETIO_CORS_ORIGINS'] = origins
        
        config_manager = WebSocketConfigManager(self.config)
        cors_manager = CORSManager(config_manager)
        
        allowed_origins = cors_manager.get_allowed_origins()
        
        self.assertIn('https://app1.example.com', allowed_origins)
        self.assertIn('https://app2.example.com', allowed_origins)
        self.assertIn('http://localhost:3000', allowed_origins)
    
    def test_wildcard_origin_handling(self):
        """Test wildcard origin handling"""
        os.environ['SOCKETIO_CORS_ORIGINS'] = '*'
        
        config_manager = WebSocketConfigManager(self.config)
        cors_manager = CORSManager(config_manager)
        
        allowed_origins = cors_manager.get_allowed_origins()
        self.assertEqual(allowed_origins, ['*'])
        
        # Wildcard should validate any origin
        self.assertTrue(cors_manager.validate_origin('https://any-domain.com'))
        self.assertTrue(cors_manager.validate_origin('http://malicious.example.com'))
    
    def test_development_vs_production_origins(self):
        """Test different origins for development vs production"""
        # Test development environment
        os.environ['FLASK_ENV'] = 'development'
        
        config_manager = WebSocketConfigManager(self.config)
        cors_manager = CORSManager(config_manager)
        
        dev_origins = cors_manager.get_allowed_origins()
        
        # Should include development ports
        dev_ports_found = any(':3000' in origin or ':8080' in origin for origin in dev_origins)
        self.assertTrue(dev_ports_found)
        
        # Test production environment
        os.environ['FLASK_ENV'] = 'production'
        
        config_manager = WebSocketConfigManager(self.config)
        cors_manager = CORSManager(config_manager)
        
        prod_origins = cors_manager.get_allowed_origins()
        
        # Should include HTTPS variants
        https_origins = [origin for origin in prod_origins if origin.startswith('https://')]
        self.assertTrue(len(https_origins) > 0)
    
    def test_custom_host_origin_generation(self):
        """Test origin generation for custom hosts"""
        test_cases = [
            ('example.com', '80', ['http://example.com', 'https://example.com']),
            ('api.myapp.com', '8443', ['http://api.myapp.com:8443', 'https://api.myapp.com:8443']),
            ('192.168.1.100', '5000', ['http://192.168.1.100:5000', 'https://192.168.1.100:5000']),
        ]
        
        for host, port, expected_patterns in test_cases:
            with self.subTest(host=host, port=port):
                os.environ['FLASK_HOST'] = host
                os.environ['FLASK_PORT'] = port
                
                config_manager = WebSocketConfigManager(self.config)
                cors_manager = CORSManager(config_manager)
                
                allowed_origins = cors_manager.get_allowed_origins()
                
                for pattern in expected_patterns:
                    self.assertTrue(
                        any(pattern in origin for origin in allowed_origins),
                        f"Pattern '{pattern}' not found in origins: {allowed_origins}"
                    )
    
    def test_origin_validation_edge_cases(self):
        """Test origin validation edge cases"""
        config_manager = WebSocketConfigManager(self.config)
        cors_manager = CORSManager(config_manager)
        
        # Test edge cases
        edge_cases = [
            ('', False),  # Empty origin
            ('http://', False),  # Invalid format
            ('https://localhost', True),  # No port
            ('http://localhost:80', True),  # Default HTTP port
            ('https://localhost:443', True),  # Default HTTPS port
            ('http://[::1]:5000', True),  # IPv6 localhost
            ('ftp://localhost:5000', False),  # Wrong protocol
            ('http://localhost:99999', False),  # Invalid port
        ]
        
        for origin, expected in edge_cases:
            with self.subTest(origin=origin):
                result = cors_manager.validate_origin(origin)
                self.assertEqual(result, expected, f"Origin '{origin}' validation failed")


class TestErrorRecoverySimulation(unittest.TestCase):
    """Error recovery testing with simulated network conditions"""
    
    def setUp(self):
        """Set up error recovery testing environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        
        # Mock database and session managers
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager
        )
    
    def test_configuration_error_recovery(self):
        """Test recovery from configuration errors"""
        # Simulate configuration loading error
        with patch.object(WebSocketConfigManager, '_create_websocket_config', side_effect=Exception("Network error")):
            config_manager = WebSocketConfigManager(self.config)
            
            # Should fall back to safe configuration
            self.assertIsNotNone(config_manager._websocket_config)
            
            # Should still provide basic functionality
            cors_origins = config_manager.get_cors_origins()
            self.assertTrue(len(cors_origins) > 0)
            
            socketio_config = config_manager.get_socketio_config()
            self.assertIsInstance(socketio_config, dict)
    
    def test_cors_validation_error_recovery(self):
        """Test CORS validation error recovery"""
        # Simulate CORS validation errors
        with patch.object(CORSManager, '_calculate_allowed_origins', side_effect=Exception("DNS error")):
            cors_manager = CORSManager(self.config_manager)
            
            # Should handle error gracefully
            try:
                origins = cors_manager.get_allowed_origins()
                # Should return empty list or cached origins
                self.assertIsInstance(origins, list)
            except Exception as e:
                self.fail(f"CORS manager should handle errors gracefully: {e}")
    
    def test_authentication_error_recovery(self):
        """Test authentication error recovery"""
        # Simulate database connection error
        self.db_manager.get_session.side_effect = Exception("Database connection lost")
        
        # Authentication should handle error gracefully
        result, context = self.auth_handler.authenticate_connection()
        
        self.assertEqual(result, AuthenticationResult.SYSTEM_ERROR)
        self.assertIsNone(context)
    
    def test_session_validation_error_recovery(self):
        """Test session validation error recovery"""
        # Simulate session manager error
        self.session_manager.get_session_data.side_effect = Exception("Redis connection lost")
        
        # Should handle error gracefully
        result, context = self.auth_handler.authenticate_connection()
        
        self.assertEqual(result, AuthenticationResult.INVALID_SESSION)
        self.assertIsNone(context)
    
    def test_rate_limiting_error_recovery(self):
        """Test rate limiting error recovery"""
        # Simulate error in rate limiting
        with patch.object(WebSocketAuthHandler, '_check_user_rate_limit', side_effect=Exception("Memory error")):
            # Should allow connection on error (fail open)
            result = self.auth_handler._check_user_rate_limit(1)
            self.assertTrue(result)
    
    def test_concurrent_error_handling(self):
        """Test error handling under concurrent load"""
        def simulate_concurrent_authentication():
            """Simulate concurrent authentication attempts"""
            results = []
            for i in range(10):
                try:
                    result, context = self.auth_handler.authenticate_connection()
                    results.append((result, context))
                except Exception as e:
                    results.append((AuthenticationResult.SYSTEM_ERROR, None))
            return results
        
        # Run concurrent simulations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(simulate_concurrent_authentication) for _ in range(3)]
            
            all_results = []
            for future in as_completed(futures):
                try:
                    results = future.result(timeout=5)
                    all_results.extend(results)
                except Exception as e:
                    self.fail(f"Concurrent error handling failed: {e}")
        
        # Should have handled all attempts
        self.assertEqual(len(all_results), 30)  # 3 threads * 10 attempts each


class TestPerformanceLoad(unittest.TestCase):
    """Performance tests for connection load and message throughput"""
    
    def setUp(self):
        """Set up performance testing environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        
        # Mock components for performance testing
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager
        )
    
    def test_configuration_loading_performance(self):
        """Test configuration loading performance"""
        start_time = time.time()
        
        # Load configuration multiple times
        for _ in range(100):
            config_manager = WebSocketConfigManager(self.config)
            config_manager.get_cors_origins()
            config_manager.get_socketio_config()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(duration, 5.0, f"Configuration loading took {duration:.2f}s for 100 iterations")
        
        # Calculate average time per configuration load
        avg_time = duration / 100
        self.assertLess(avg_time, 0.05, f"Average configuration load time: {avg_time:.3f}s")
    
    def test_cors_validation_performance(self):
        """Test CORS validation performance"""
        origins_to_test = [
            'http://localhost:5000',
            'https://127.0.0.1:5000',
            'http://localhost:3000',
            'https://example.com',
            'http://malicious.com',
            'invalid-origin',
        ] * 100  # 600 total validations
        
        start_time = time.time()
        
        for origin in origins_to_test:
            self.cors_manager.validate_origin(origin)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should validate 600 origins quickly
        self.assertLess(duration, 2.0, f"CORS validation took {duration:.2f}s for 600 origins")
        
        # Calculate validations per second
        validations_per_second = len(origins_to_test) / duration
        self.assertGreater(validations_per_second, 300, f"CORS validation rate: {validations_per_second:.0f}/s")
    
    def test_authentication_performance(self):
        """Test authentication performance"""
        # Mock successful authentication
        self.session_manager.get_session_data.return_value = {
            'user_id': 1,
            'username': 'testuser',
            'role': 'admin'
        }
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.email = 'test@example.com'
        mock_user.role = UserRole.ADMIN
        mock_user.is_active = True
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        start_time = time.time()
        
        # Perform multiple authentications
        for i in range(100):
            with patch('websocket_auth_handler.request') as mock_request:
                mock_request.headers.get.side_effect = lambda header, default=None: {
                    'X-Forwarded-For': '192.168.1.100',
                    'User-Agent': 'Test Client'
                }.get(header, default)
                mock_request.remote_addr = '192.168.1.100'
                
                result, context = self.auth_handler.authenticate_connection(
                    auth_data={'session_id': f'test-session-{i}'}
                )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should authenticate 100 users quickly
        self.assertLess(duration, 3.0, f"Authentication took {duration:.2f}s for 100 users")
        
        # Calculate authentications per second
        auth_per_second = 100 / duration
        self.assertGreater(auth_per_second, 30, f"Authentication rate: {auth_per_second:.0f}/s")
    
    def test_concurrent_authentication_performance(self):
        """Test concurrent authentication performance"""
        # Mock successful authentication
        self.session_manager.get_session_data.return_value = {
            'user_id': 1,
            'username': 'testuser',
            'role': 'admin'
        }
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.email = 'test@example.com'
        mock_user.role = UserRole.ADMIN
        mock_user.is_active = True
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        def authenticate_user(user_id):
            """Authenticate a single user"""
            with patch('websocket_auth_handler.request') as mock_request:
                mock_request.headers.get.side_effect = lambda header, default=None: {
                    'X-Forwarded-For': f'192.168.1.{user_id % 255}',
                    'User-Agent': 'Test Client'
                }.get(header, default)
                mock_request.remote_addr = f'192.168.1.{user_id % 255}'
                
                return self.auth_handler.authenticate_connection(
                    auth_data={'session_id': f'test-session-{user_id}'}
                )
        
        start_time = time.time()
        
        # Run concurrent authentications
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(authenticate_user, i) for i in range(50)]
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=5)
                    results.append(result)
                except Exception as e:
                    self.fail(f"Concurrent authentication failed: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle 50 concurrent authentications
        self.assertEqual(len(results), 50)
        self.assertLess(duration, 5.0, f"Concurrent authentication took {duration:.2f}s for 50 users")
        
        # Calculate concurrent authentications per second
        concurrent_auth_per_second = 50 / duration
        self.assertGreater(concurrent_auth_per_second, 10, f"Concurrent auth rate: {concurrent_auth_per_second:.0f}/s")
    
    def test_rate_limiting_performance(self):
        """Test rate limiting performance under load"""
        start_time = time.time()
        
        # Test rate limiting for many users and IPs
        for user_id in range(100):
            for attempt in range(5):  # 5 attempts per user
                self.auth_handler._check_user_rate_limit(user_id)
        
        for ip_suffix in range(50):
            ip = f'192.168.1.{ip_suffix}'
            for attempt in range(10):  # 10 attempts per IP
                self.auth_handler._check_ip_rate_limit(ip)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle 1000 rate limit checks quickly
        total_checks = (100 * 5) + (50 * 10)  # 1000 total checks
        self.assertLess(duration, 2.0, f"Rate limiting took {duration:.2f}s for {total_checks} checks")
        
        # Calculate rate limit checks per second
        checks_per_second = total_checks / duration
        self.assertGreater(checks_per_second, 500, f"Rate limit check rate: {checks_per_second:.0f}/s")
    
    def test_memory_usage_under_load(self):
        """Test memory usage under sustained load"""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate sustained load
        for iteration in range(10):
            # Create many authentication attempts
            for user_id in range(100):
                self.auth_handler._check_user_rate_limit(user_id)
                
            for ip_suffix in range(100):
                ip = f'10.0.{iteration}.{ip_suffix}'
                self.auth_handler._check_ip_rate_limit(ip)
            
            # Periodically clean up
            if iteration % 3 == 0:
                self.auth_handler.cleanup_old_data()
                gc.collect()
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (adjust threshold as needed)
        self.assertLess(memory_increase, 50, f"Memory increased by {memory_increase:.1f}MB under load")


class TestWebSocketTestRunner(unittest.TestCase):
    """Test runner for comprehensive WebSocket testing"""
    
    def test_run_all_websocket_tests(self):
        """Run all WebSocket tests and collect results"""
        test_classes = [
            TestWebSocketConfigManager,
            TestCORSManager,
            TestWebSocketAuthHandler,
            TestWebSocketFactory,
            TestWebSocketIntegration,
            TestCORSMultipleOrigins,
            TestErrorRecoverySimulation,
            TestPerformanceLoad,
        ]
        
        suite = unittest.TestSuite()
        
        for test_class in test_classes:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        # Run tests with detailed results
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(suite)
        
        # Verify all tests passed
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])
        self.assertTrue(result.wasSuccessful())


def run_comprehensive_websocket_tests():
    """Run comprehensive WebSocket CORS standardization tests"""
    print("🧪 Running Comprehensive WebSocket CORS Standardization Tests")
    print("=" * 70)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestWebSocketConfigManager,
        TestCORSManager,
        TestWebSocketAuthHandler,
        TestWebSocketFactory,
        TestWebSocketIntegration,
        TestCORSMultipleOrigins,
        TestErrorRecoverySimulation,
        TestPerformanceLoad,
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('\\n')[-2]}")
    
    if result.wasSuccessful():
        print("\n✅ All WebSocket CORS standardization tests passed!")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_comprehensive_websocket_tests()
    sys.exit(0 if success else 1)
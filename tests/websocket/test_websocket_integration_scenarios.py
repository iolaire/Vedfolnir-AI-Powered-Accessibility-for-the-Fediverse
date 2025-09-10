# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Integration Test Scenarios

This module provides comprehensive integration tests for end-to-end WebSocket
connection scenarios, including real connection testing, namespace integration,
authentication flow testing, and cross-browser compatibility scenarios.
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

from flask import Flask
from flask_socketio import SocketIO, emit, disconnect
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_auth_handler import WebSocketAuthHandler, AuthenticationResult
from websocket_factory import WebSocketFactory
from websocket_namespace_manager import WebSocketNamespaceManager
from session_manager_v2 import SessionManagerV2


class TestWebSocketConnectionScenarios(unittest.TestCase):
    """Integration tests for WebSocket connection scenarios"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.config = Config()
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Initialize WebSocket components
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        self.factory = WebSocketFactory(self.config_manager, self.cors_manager)
        
        # Mock database and session managers
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager
        )
    
    def test_socketio_instance_creation(self):
        """Test SocketIO instance creation with factory"""
        try:
            # Create SocketIO instance using factory
            socketio = self.factory.create_test_socketio_instance(self.app)
            
            self.assertIsNotNone(socketio)
            self.assertIsInstance(socketio, SocketIO)
            
            # Test configuration was applied
            self.assertTrue(hasattr(socketio, 'server'))
            
        except Exception as e:
            self.fail(f"Failed to create SocketIO instance: {e}")
    
    def test_namespace_configuration(self):
        """Test namespace configuration integration"""
        socketio = self.factory.create_test_socketio_instance(self.app)
        
        # Configure namespaces
        namespace_configs = {
            '/': {
                'description': 'Default user namespace',
                'auth_required': True,
            },
            '/admin': {
                'description': 'Admin namespace',
                'auth_required': True,
                'admin_only': True,
            }
        }
        
        try:
            self.factory.configure_namespaces(socketio, namespace_configs)
            
            # Test that namespaces were configured
            # This is a basic test since we can't easily inspect SocketIO internals
            self.assertTrue(True)  # If no exception, configuration succeeded
            
        except Exception as e:
            self.fail(f"Failed to configure namespaces: {e}")
    
    def test_cors_integration_with_socketio(self):
        """Test CORS integration with SocketIO configuration"""
        # Set specific CORS origins
        os.environ['SOCKETIO_CORS_ORIGINS'] = 'http://localhost:3000,https://app.example.com'
        
        try:
            config_manager = WebSocketConfigManager(self.config)
            cors_manager = CORSManager(config_manager)
            factory = WebSocketFactory(config_manager, cors_manager)
            
            # Create SocketIO instance
            socketio = factory.create_test_socketio_instance(self.app)
            
            # Test CORS configuration was applied
            socketio_config = factory._get_unified_socketio_config()
            
            self.assertIn('http://localhost:3000', socketio_config['cors_allowed_origins'])
            self.assertIn('https://app.example.com', socketio_config['cors_allowed_origins'])
            
        finally:
            if 'SOCKETIO_CORS_ORIGINS' in os.environ:
                del os.environ['SOCKETIO_CORS_ORIGINS']
    
    def test_authentication_integration_flow(self):
        """Test complete authentication integration flow"""
        # Mock successful authentication setup
        self.session_manager.get_session_data.return_value = {
            'user_id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
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
        
        # Test authentication flow
        with patch('websocket_auth_handler.request') as mock_request:
            mock_request.headers.get.side_effect = lambda header, default=None: {
                'X-Forwarded-For': '192.168.1.100',
                'User-Agent': 'Test Client'
            }.get(header, default)
            mock_request.remote_addr = '192.168.1.100'
            
            result, context = self.auth_handler.authenticate_connection(
                auth_data={'session_id': 'test-session-123'},
                namespace='/'
            )
            
            self.assertEqual(result, AuthenticationResult.SUCCESS)
            self.assertIsNotNone(context)
            self.assertEqual(context.user_id, 1)
            self.assertEqual(context.username, 'testuser')
            self.assertTrue(context.is_admin)
    
    def test_error_handler_integration(self):
        """Test error handler integration"""
        socketio = self.factory.create_test_socketio_instance(self.app)
        
        # Test that error handlers were set up
        self.factory.setup_error_handlers(socketio)
        
        # This is a basic test since we can't easily trigger errors in test environment
        self.assertTrue(True)  # If no exception, error handlers were set up
    
    def test_middleware_integration(self):
        """Test middleware integration"""
        middleware_called = []
        
        def test_middleware(socketio_instance):
            middleware_called.append(True)
        
        self.factory.register_middleware(test_middleware)
        
        # Create SocketIO instance (should apply middleware)
        socketio = self.factory.create_test_socketio_instance(self.app)
        
        # Verify middleware was called
        self.assertTrue(len(middleware_called) > 0)
    
    def test_configuration_validation_integration(self):
        """Test configuration validation across all components"""
        # Test valid configuration
        self.assertTrue(self.factory.validate_factory_configuration())
        
        # Test with invalid configuration
        with patch.object(WebSocketConfigManager, 'validate_configuration', return_value=False):
            self.assertFalse(self.factory.validate_factory_configuration())


class TestWebSocketNamespaceIntegration(unittest.TestCase):
    """Integration tests for WebSocket namespace functionality"""
    
    def setUp(self):
        """Set up namespace integration test environment"""
        self.config = Config()
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Initialize components
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        self.factory = WebSocketFactory(self.config_manager, self.cors_manager)
        
        # Mock dependencies
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager
        )
        
        # Create SocketIO instance
        self.socketio = self.factory.create_test_socketio_instance(self.app)
        
        # Create namespace manager
        self.namespace_manager = WebSocketNamespaceManager(self.socketio, self.auth_handler)
    
    def test_user_namespace_setup(self):
        """Test user namespace setup and configuration"""
        try:
            self.namespace_manager.setup_user_namespace()
            
            # Test that user namespace was configured
            # This is a basic test since we can't easily inspect namespace internals
            self.assertTrue(True)  # If no exception, setup succeeded
            
        except Exception as e:
            self.fail(f"Failed to setup user namespace: {e}")
    
    def test_admin_namespace_setup(self):
        """Test admin namespace setup and configuration"""
        try:
            self.namespace_manager.setup_admin_namespace()
            
            # Test that admin namespace was configured
            self.assertTrue(True)  # If no exception, setup succeeded
            
        except Exception as e:
            self.fail(f"Failed to setup admin namespace: {e}")
    
    def test_namespace_authentication_integration(self):
        """Test namespace authentication integration"""
        # Mock successful authentication
        self.session_manager.get_session_data.return_value = {
            'user_id': 1,
            'username': 'admin',
            'role': 'admin'
        }
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.role = UserRole.ADMIN
        mock_user.is_active = True
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Test authentication for different namespaces
        namespaces = ['/', '/admin']
        
        for namespace in namespaces:
            with self.subTest(namespace=namespace):
                with patch('websocket_auth_handler.request') as mock_request:
                    mock_request.headers.get.return_value = 'Test Client'
                    mock_request.remote_addr = '127.0.0.1'
                    
                    result, context = self.auth_handler.authenticate_connection(
                        auth_data={'session_id': 'test-session'},
                        namespace=namespace
                    )
                    
                    self.assertEqual(result, AuthenticationResult.SUCCESS)
                    self.assertIsNotNone(context)
    
    def test_event_handler_registration(self):
        """Test event handler registration for namespaces"""
        handlers_registered = []
        
        def test_handler():
            handlers_registered.append(True)
        
        handlers = {
            'test_event': test_handler
        }
        
        try:
            self.namespace_manager.register_event_handlers('/', handlers)
            
            # Test that handlers were registered
            # This is a basic test since we can't easily trigger events
            self.assertTrue(True)  # If no exception, registration succeeded
            
        except Exception as e:
            self.fail(f"Failed to register event handlers: {e}")


class TestWebSocketAuthenticationFlow(unittest.TestCase):
    """Integration tests for WebSocket authentication flow"""
    
    def setUp(self):
        """Set up authentication flow test environment"""
        self.config = Config()
        
        # Mock dependencies
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_manager = Mock(spec=SessionManagerV2)
        
        self.auth_handler = WebSocketAuthHandler(
            db_manager=self.db_manager,
            session_manager=self.session_manager
        )
    
    def test_complete_authentication_flow(self):
        """Test complete authentication flow from session to context"""
        # Setup mock data
        session_data = {
            'user_id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'role': 'reviewer',
            'platform_connection_id': 123,
            'platform_name': 'Test Platform',
            'platform_type': 'mastodon'
        }
        self.session_manager.get_session_data.return_value = session_data
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.email = 'test@example.com'
        mock_user.role = UserRole.REVIEWER
        mock_user.is_active = True
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Test authentication
        with patch('websocket_auth_handler.request') as mock_request:
            mock_request.headers.get.side_effect = lambda header, default=None: {
                'X-Forwarded-For': '192.168.1.100',
                'User-Agent': 'Test Client'
            }.get(header, default)
            mock_request.remote_addr = '192.168.1.100'
            
            result, context = self.auth_handler.authenticate_connection(
                auth_data={'session_id': 'test-session-123'}
            )
            
            # Verify authentication result
            self.assertEqual(result, AuthenticationResult.SUCCESS)
            self.assertIsNotNone(context)
            
            # Verify context data
            self.assertEqual(context.user_id, 1)
            self.assertEqual(context.username, 'testuser')
            self.assertEqual(context.email, 'test@example.com')
            self.assertEqual(context.role, UserRole.REVIEWER)
            self.assertEqual(context.platform_connection_id, 123)
            self.assertEqual(context.platform_name, 'Test Platform')
            self.assertEqual(context.platform_type, 'mastodon')
            self.assertFalse(context.is_admin)
    
    def test_authentication_failure_scenarios(self):
        """Test various authentication failure scenarios"""
        failure_scenarios = [
            # No session data
            {
                'session_data': None,
                'expected_result': AuthenticationResult.INVALID_SESSION,
                'description': 'No session data'
            },
            # Session without user_id
            {
                'session_data': {'username': 'test'},
                'expected_result': AuthenticationResult.INVALID_SESSION,
                'description': 'Session without user_id'
            },
            # User not found
            {
                'session_data': {'user_id': 999},
                'user': None,
                'expected_result': AuthenticationResult.USER_NOT_FOUND,
                'description': 'User not found'
            },
            # Inactive user
            {
                'session_data': {'user_id': 1},
                'user': Mock(id=1, is_active=False),
                'expected_result': AuthenticationResult.USER_INACTIVE,
                'description': 'Inactive user'
            }
        ]
        
        for scenario in failure_scenarios:
            with self.subTest(description=scenario['description']):
                # Setup scenario
                self.session_manager.get_session_data.return_value = scenario['session_data']
                
                if 'user' in scenario:
                    mock_db_session = Mock()
                    mock_db_session.get.return_value = scenario['user']
                    self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
                
                # Test authentication
                with patch('websocket_auth_handler.request') as mock_request:
                    mock_request.headers.get.return_value = 'Test Client'
                    mock_request.remote_addr = '127.0.0.1'
                    
                    result, context = self.auth_handler.authenticate_connection(
                        auth_data={'session_id': 'test-session'}
                    )
                    
                    self.assertEqual(result, scenario['expected_result'])
                    self.assertIsNone(context)
    
    def test_admin_authorization_flow(self):
        """Test admin authorization flow"""
        # Create admin context
        admin_context = Mock()
        admin_context.user_id = 1
        admin_context.username = 'admin'
        admin_context.session_id = 'admin-session'
        admin_context.is_admin = True
        admin_context.permissions = ['system_management', 'user_management']
        
        # Test admin authorization
        self.assertTrue(self.auth_handler.authorize_admin_access(admin_context))
        self.assertTrue(self.auth_handler.authorize_admin_access(admin_context, 'system_management'))
        self.assertFalse(self.auth_handler.authorize_admin_access(admin_context, 'nonexistent_permission'))
        
        # Create non-admin context
        user_context = Mock()
        user_context.user_id = 2
        user_context.username = 'user'
        user_context.session_id = 'user-session'
        user_context.is_admin = False
        user_context.permissions = []
        
        # Test non-admin authorization
        self.assertFalse(self.auth_handler.authorize_admin_access(user_context))
    
    def test_session_validation_flow(self):
        """Test session validation flow"""
        # Setup valid session
        session_data = {'user_id': 1}
        self.session_manager.get_session_data.return_value = session_data
        
        mock_user = Mock()
        mock_user.is_active = True
        
        mock_db_session = Mock()
        mock_db_session.get.return_value = mock_user
        self.db_manager.get_session.return_value.__enter__.return_value = mock_db_session
        
        # Test valid session
        self.assertTrue(self.auth_handler.validate_user_session(1, 'test-session'))
        
        # Test invalid session (no session data)
        self.session_manager.get_session_data.return_value = None
        self.assertFalse(self.auth_handler.validate_user_session(1, 'invalid-session'))
        
        # Test session user mismatch
        self.session_manager.get_session_data.return_value = {'user_id': 2}
        self.assertFalse(self.auth_handler.validate_user_session(1, 'mismatched-session'))


class TestWebSocketCrossBrowserCompatibility(unittest.TestCase):
    """Integration tests for cross-browser compatibility scenarios"""
    
    def setUp(self):
        """Set up cross-browser compatibility test environment"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
    
    def test_browser_specific_origins(self):
        """Test browser-specific origin handling"""
        browser_origins = [
            # Chrome/Chromium
            'http://localhost:5000',
            'https://localhost:5000',
            # Firefox
            'http://127.0.0.1:5000',
            'https://127.0.0.1:5000',
            # Safari (may use different localhost resolution)
            'http://localhost.localdomain:5000',
            # Edge
            'http://localhost:5000',
        ]
        
        for origin in browser_origins:
            with self.subTest(origin=origin):
                # Most should be valid for localhost testing
                if 'localhost' in origin or '127.0.0.1' in origin:
                    self.assertTrue(self.cors_manager.validate_origin(origin))
    
    def test_transport_fallback_scenarios(self):
        """Test transport fallback scenarios for different browsers"""
        transport_scenarios = [
            # Modern browsers - WebSocket preferred
            ['websocket', 'polling'],
            # Older browsers - polling only
            ['polling'],
            # Corporate networks - polling preferred
            ['polling', 'websocket'],
        ]
        
        for transports in transport_scenarios:
            with self.subTest(transports=transports):
                # Set transport configuration
                os.environ['SOCKETIO_TRANSPORTS'] = ','.join(transports)
                
                try:
                    config_manager = WebSocketConfigManager(self.config)
                    socketio_config = config_manager.get_socketio_config()
                    
                    self.assertEqual(socketio_config['transports'], transports)
                    
                finally:
                    if 'SOCKETIO_TRANSPORTS' in os.environ:
                        del os.environ['SOCKETIO_TRANSPORTS']
    
    def test_protocol_detection_scenarios(self):
        """Test protocol detection for different deployment scenarios"""
        protocol_scenarios = [
            # Direct HTTP
            {'headers': {}, 'expected': 'http'},
            # HTTPS with X-Forwarded-Proto
            {'headers': {'X-Forwarded-Proto': 'https'}, 'expected': 'https'},
            # HTTPS with X-Forwarded-SSL
            {'headers': {'X-Forwarded-SSL': 'on'}, 'expected': 'https'},
            # Mixed case headers
            {'headers': {'x-forwarded-proto': 'HTTPS'}, 'expected': 'https'},
        ]
        
        for scenario in protocol_scenarios:
            with self.subTest(scenario=scenario):
                with patch('websocket_cors_manager.request') as mock_request:
                    mock_request.headers.get.side_effect = lambda header, default=None: \
                        scenario['headers'].get(header, scenario['headers'].get(header.lower(), default))
                    mock_request.is_secure = scenario['expected'] == 'https'
                    
                    detected_protocol = self.cors_manager.detect_protocol_from_request()
                    self.assertEqual(detected_protocol, scenario['expected'])
    
    def test_port_handling_scenarios(self):
        """Test port handling for different browser behaviors"""
        port_scenarios = [
            # Standard ports
            ('localhost', '80', 'http://localhost'),
            ('localhost', '443', 'https://localhost'),
            # Non-standard ports
            ('localhost', '3000', 'http://localhost:3000'),
            ('localhost', '8443', 'https://localhost:8443'),
            # IPv4 addresses
            ('127.0.0.1', '5000', 'http://127.0.0.1:5000'),
            # Custom domains
            ('app.example.com', '8080', 'http://app.example.com:8080'),
        ]
        
        for host, port, expected_pattern in port_scenarios:
            with self.subTest(host=host, port=port):
                os.environ['FLASK_HOST'] = host
                os.environ['FLASK_PORT'] = port
                
                try:
                    config_manager = WebSocketConfigManager(self.config)
                    cors_manager = CORSManager(config_manager)
                    
                    allowed_origins = cors_manager.get_allowed_origins()
                    
                    # Check if expected pattern is in allowed origins
                    pattern_found = any(expected_pattern in origin for origin in allowed_origins)
                    self.assertTrue(pattern_found, f"Pattern '{expected_pattern}' not found in {allowed_origins}")
                    
                finally:
                    if 'FLASK_HOST' in os.environ:
                        del os.environ['FLASK_HOST']
                    if 'FLASK_PORT' in os.environ:
                        del os.environ['FLASK_PORT']


def run_integration_tests():
    """Run all WebSocket integration tests"""
    print("🔗 Running WebSocket Integration Test Scenarios")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestWebSocketConnectionScenarios,
        TestWebSocketNamespaceIntegration,
        TestWebSocketAuthenticationFlow,
        TestWebSocketCrossBrowserCompatibility,
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Integration Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ All WebSocket integration tests passed!")
    else:
        print("\n❌ Some integration tests failed. Please review the output above.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)
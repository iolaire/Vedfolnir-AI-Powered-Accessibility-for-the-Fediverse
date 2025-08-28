# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for WebSocket Factory

Tests the WebSocket factory functionality including SocketIO instance creation,
configuration management, namespace setup, and error handling.
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websocket_factory import WebSocketFactory
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from config import Config


class TestWebSocketFactory(unittest.TestCase):
    """Test cases for WebSocket Factory"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock config
        self.mock_config = Mock(spec=Config)
        
        # Create config manager
        self.config_manager = WebSocketConfigManager(self.mock_config)
        
        # Create CORS manager
        self.cors_manager = CORSManager(self.config_manager)
        
        # Create WebSocket factory
        self.factory = WebSocketFactory(self.config_manager, self.cors_manager)
        
        # Create test Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
    
    def test_factory_initialization(self):
        """Test WebSocket factory initialization"""
        self.assertIsNotNone(self.factory)
        self.assertEqual(self.factory.config_manager, self.config_manager)
        self.assertEqual(self.factory.cors_manager, self.cors_manager)
        self.assertIsInstance(self.factory._error_handlers, dict)
        self.assertIsInstance(self.factory._namespace_handlers, dict)
        self.assertIsInstance(self.factory._middleware_functions, list)
    
    @patch('websocket_factory.SocketIO')
    def test_create_socketio_instance(self, mock_socketio_class):
        """Test SocketIO instance creation"""
        # Setup mock
        mock_socketio_instance = Mock()
        mock_socketio_class.return_value = mock_socketio_instance
        
        # Create SocketIO instance
        result = self.factory.create_socketio_instance(self.app)
        
        # Verify SocketIO was created
        self.assertEqual(result, mock_socketio_instance)
        mock_socketio_class.assert_called_once()
        
        # Verify the app was passed as first argument
        call_args = mock_socketio_class.call_args
        self.assertEqual(call_args[0][0], self.app)
        
        # Verify configuration was passed
        config_kwargs = call_args[1]
        self.assertIn('cors_allowed_origins', config_kwargs)
        self.assertIn('async_mode', config_kwargs)
        self.assertIn('transports', config_kwargs)
    
    def test_get_unified_socketio_config(self):
        """Test unified SocketIO configuration generation"""
        config = self.factory._get_unified_socketio_config()
        
        # Verify required configuration keys
        self.assertIn('cors_allowed_origins', config)
        self.assertIn('cors_credentials', config)
        self.assertIn('async_mode', config)
        self.assertIn('transports', config)
        self.assertIn('ping_timeout', config)
        self.assertIn('ping_interval', config)
        self.assertIn('logger', config)
        self.assertIn('engineio_logger', config)
        
        # Verify logger settings
        self.assertTrue(config['logger'])
        self.assertFalse(config['engineio_logger'])
    
    @patch('websocket_factory.SocketIO')
    def test_configure_namespaces(self, mock_socketio_class):
        """Test namespace configuration"""
        # Setup mock
        mock_socketio_instance = Mock()
        mock_socketio_class.return_value = mock_socketio_instance
        
        # Create SocketIO instance
        socketio = self.factory.create_socketio_instance(self.app)
        
        # Test namespace configuration
        namespace_configs = {
            '/test': {
                'handlers': {
                    'test_event': lambda: None
                },
                'auth_required': True
            }
        }
        
        # This should not raise an exception
        self.factory.configure_namespaces(socketio, namespace_configs)
    
    def test_register_middleware(self):
        """Test middleware registration"""
        # Create test middleware function
        def test_middleware(socketio):
            pass
        
        # Register middleware
        self.factory.register_middleware(test_middleware)
        
        # Verify middleware was registered
        self.assertIn(test_middleware, self.factory._middleware_functions)
    
    def test_register_error_handler(self):
        """Test error handler registration"""
        # Create test error handler
        def test_error_handler(error):
            pass
        
        # Register error handler
        self.factory.register_error_handler('test_error', test_error_handler)
        
        # Verify error handler was registered
        self.assertIn('test_error', self.factory._error_handlers)
        self.assertEqual(self.factory._error_handlers['test_error'], test_error_handler)
    
    def test_analyze_connection_error(self):
        """Test connection error analysis"""
        # Test CORS error
        cors_error = "CORS policy error"
        self.assertEqual(self.factory._analyze_connection_error(cors_error), 'cors_error')
        
        # Test timeout error
        timeout_error = "Connection timeout"
        self.assertEqual(self.factory._analyze_connection_error(timeout_error), 'timeout_error')
        
        # Test transport error
        transport_error = "Transport failed"
        self.assertEqual(self.factory._analyze_connection_error(transport_error), 'transport_error')
        
        # Test auth error
        auth_error = "Unauthorized access"
        self.assertEqual(self.factory._analyze_connection_error(auth_error), 'auth_error')
        
        # Test unknown error
        unknown_error = "Some other error"
        self.assertEqual(self.factory._analyze_connection_error(unknown_error), 'unknown_error')
    
    def test_get_current_timestamp(self):
        """Test timestamp generation"""
        timestamp = self.factory._get_current_timestamp()
        
        # Verify timestamp format
        self.assertIsInstance(timestamp, str)
        self.assertTrue(timestamp.endswith('Z'))
        self.assertIn('T', timestamp)  # ISO format should contain 'T'
    
    def test_get_factory_status(self):
        """Test factory status information"""
        status = self.factory.get_factory_status()
        
        # Verify status structure
        self.assertIn('config_manager_status', status)
        self.assertIn('cors_debug_info', status)
        self.assertIn('registered_middleware', status)
        self.assertIn('registered_error_handlers', status)
        self.assertIn('namespace_handlers', status)
        
        # Verify types
        self.assertIsInstance(status['registered_middleware'], int)
        self.assertIsInstance(status['registered_error_handlers'], list)
        self.assertIsInstance(status['namespace_handlers'], list)
    
    def test_validate_factory_configuration(self):
        """Test factory configuration validation"""
        # This should return True for valid configuration
        is_valid = self.factory.validate_factory_configuration()
        
        # The result depends on the configuration, but should not raise an exception
        self.assertIsInstance(is_valid, bool)
    
    @patch('websocket_factory.SocketIO')
    def test_create_test_socketio_instance(self, mock_socketio_class):
        """Test test SocketIO instance creation"""
        # Setup mock
        mock_socketio_instance = Mock()
        mock_socketio_class.return_value = mock_socketio_instance
        
        # Test configuration overrides
        test_config = {
            'ping_timeout': 30,
            'ping_interval': 10
        }
        
        # Create test SocketIO instance
        result = self.factory.create_test_socketio_instance(self.app, test_config)
        
        # Verify SocketIO was created
        self.assertEqual(result, mock_socketio_instance)
        mock_socketio_class.assert_called_once()
        
        # Verify test configuration was applied
        call_args = mock_socketio_class.call_args
        config_kwargs = call_args[1]
        self.assertEqual(config_kwargs['ping_timeout'], 30)
        self.assertEqual(config_kwargs['ping_interval'], 10)
    
    @patch('websocket_factory.SocketIO')
    def test_error_handler_setup(self, mock_socketio_class):
        """Test error handler setup"""
        # Setup mock
        mock_socketio_instance = Mock()
        mock_socketio_class.return_value = mock_socketio_instance
        
        # Create SocketIO instance (this should setup error handlers)
        self.factory.create_socketio_instance(self.app)
        
        # Verify error handlers were registered
        # The mock should have been called with on_error_default and on_error methods
        self.assertTrue(mock_socketio_instance.on_error_default.called)
    
    def test_factory_with_invalid_config(self):
        """Test factory behavior with invalid configuration"""
        # Create factory with invalid config manager
        invalid_config_manager = Mock()
        invalid_config_manager.get_socketio_config.side_effect = Exception("Config error")
        
        invalid_factory = WebSocketFactory(invalid_config_manager, self.cors_manager)
        
        # Creating SocketIO instance should raise an error
        with self.assertRaises(RuntimeError):
            invalid_factory.create_socketio_instance(self.app)


class TestWebSocketFactoryIntegration(unittest.TestCase):
    """Integration tests for WebSocket Factory"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        # Set test environment variables
        os.environ['FLASK_HOST'] = '127.0.0.1'
        os.environ['FLASK_PORT'] = '5000'
        os.environ['SOCKETIO_ASYNC_MODE'] = 'threading'
        os.environ['SOCKETIO_TRANSPORTS'] = 'websocket,polling'
        
        # Create real config
        self.config = Config()
        
        # Create real managers
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        
        # Create factory
        self.factory = WebSocketFactory(self.config_manager, self.cors_manager)
        
        # Create test Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
    
    def tearDown(self):
        """Clean up test environment"""
        # Clean up environment variables
        test_vars = ['FLASK_HOST', 'FLASK_PORT', 'SOCKETIO_ASYNC_MODE', 'SOCKETIO_TRANSPORTS']
        for var in test_vars:
            if var in os.environ:
                del os.environ[var]
    
    def test_real_configuration_loading(self):
        """Test real configuration loading and validation"""
        # Validate configuration
        is_valid = self.factory.validate_factory_configuration()
        self.assertTrue(is_valid)
        
        # Get configuration summary
        status = self.factory.get_factory_status()
        self.assertIn('config_manager_status', status)
        
        # Verify CORS origins were generated
        cors_origins = self.cors_manager.get_allowed_origins()
        self.assertGreater(len(cors_origins), 0)
    
    @patch('websocket_factory.SocketIO')
    def test_real_socketio_creation(self, mock_socketio_class):
        """Test real SocketIO instance creation with actual configuration"""
        # Setup mock
        mock_socketio_instance = Mock()
        mock_socketio_class.return_value = mock_socketio_instance
        
        # Create SocketIO instance
        result = self.factory.create_socketio_instance(self.app)
        
        # Verify creation was successful
        self.assertEqual(result, mock_socketio_instance)
        
        # Verify configuration was properly loaded
        call_args = mock_socketio_class.call_args
        config_kwargs = call_args[1]
        
        # Check that real configuration values were used
        self.assertIn('cors_allowed_origins', config_kwargs)
        self.assertEqual(config_kwargs['async_mode'], 'threading')
        self.assertIn('websocket', config_kwargs['transports'])
        self.assertIn('polling', config_kwargs['transports'])


if __name__ == '__main__':
    unittest.main()
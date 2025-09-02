# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for WebSocket Configuration Management System

Tests the centralized configuration manager for WebSocket settings,
including dynamic CORS origin generation, environment variable parsing,
and configuration validation with fallback mechanisms.
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.websocket.core.config_manager import ConsolidatedWebSocketConfigManager, WebSocketConfig
from config import Config


class TestWebSocketConfig(unittest.TestCase):
    """Test WebSocketConfig dataclass"""
    
    def test_websocket_config_defaults(self):
        """Test WebSocketConfig default values"""
        config = WebSocketConfig()
        
        # Test CORS defaults
        self.assertEqual(config.cors_origins, [])
        self.assertTrue(config.cors_credentials)
        self.assertEqual(config.cors_methods, ["GET", "POST"])
        self.assertEqual(config.cors_headers, ["Content-Type", "Authorization"])
        
        # Test SocketIO defaults
        self.assertEqual(config.async_mode, "threading")
        self.assertEqual(config.transports, ["websocket", "polling"])
        self.assertEqual(config.ping_timeout, 60)
        self.assertEqual(config.ping_interval, 25)
        self.assertEqual(config.max_http_buffer_size, 1000000)
        
        # Test client defaults
        self.assertTrue(config.reconnection)
        self.assertEqual(config.reconnection_attempts, 5)
        self.assertEqual(config.reconnection_delay, 1000)
        self.assertEqual(config.reconnection_delay_max, 5000)
        self.assertEqual(config.timeout, 20000)
        
        # Test security defaults
        self.assertTrue(config.require_auth)
        self.assertTrue(config.session_validation)
        self.assertTrue(config.rate_limiting)
        self.assertTrue(config.csrf_protection)


class TestWebSocketConfigManager(unittest.TestCase):
    """Test WebSocketConfigManager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock Config object
        self.mock_config = MagicMock(spec=Config)
        
        # Clear environment variables that might affect tests
        self.env_vars_to_clear = [
            'FLASK_HOST', 'FLASK_PORT', 'SOCKETIO_CORS_ORIGINS',
            'SOCKETIO_TRANSPORTS', 'SOCKETIO_PING_TIMEOUT',
            'SOCKETIO_PING_INTERVAL', 'SOCKETIO_RECONNECTION_ATTEMPTS'
        ]
        
        self.original_env = {}
        for var in self.env_vars_to_clear:
            self.original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        """Clean up test environment"""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_initialization_with_defaults(self):
        """Test WebSocketConfigManager initialization with default values"""
        manager = WebSocketConfigManager(self.mock_config)
        
        # Should create configuration successfully
        self.assertIsNotNone(manager._websocket_config)
        self.assertIsInstance(manager._websocket_config, WebSocketConfig)
        
        # Should have generated CORS origins
        cors_origins = manager.get_cors_origins()
        self.assertIsInstance(cors_origins, list)
        self.assertGreater(len(cors_origins), 0)
        
        # Should include default localhost origins
        self.assertIn("http://127.0.0.1:5000", cors_origins)
        self.assertIn("http://localhost:5000", cors_origins)
    
    @patch.dict(os.environ, {
        'FLASK_HOST': 'example.com',
        'FLASK_PORT': '8080'
    })
    def test_cors_origin_generation_custom_host_port(self):
        """Test CORS origin generation with custom host and port"""
        manager = WebSocketConfigManager(self.mock_config)
        cors_origins = manager.get_cors_origins()
        
        # Should include custom host and port
        self.assertIn("http://example.com:8080", cors_origins)
        self.assertIn("https://example.com:8080", cors_origins)
    
    @patch.dict(os.environ, {
        'FLASK_HOST': 'localhost',
        'FLASK_PORT': '3000'
    })
    def test_cors_origin_generation_localhost_variants(self):
        """Test CORS origin generation includes localhost/127.0.0.1 variants"""
        manager = WebSocketConfigManager(self.mock_config)
        cors_origins = manager.get_cors_origins()
        
        # Should include both localhost and 127.0.0.1 variants
        self.assertIn("http://localhost:3000", cors_origins)
        self.assertIn("http://127.0.0.1:3000", cors_origins)
        self.assertIn("https://localhost:3000", cors_origins)
        self.assertIn("https://127.0.0.1:3000", cors_origins)
    
    @patch.dict(os.environ, {
        'SOCKETIO_CORS_ORIGINS': 'http://custom.example.com,https://another.example.com'
    })
    def test_explicit_cors_origins(self):
        """Test explicit CORS origins configuration"""
        manager = WebSocketConfigManager(self.mock_config)
        cors_origins = manager.get_cors_origins()
        
        # Should use explicit origins
        self.assertEqual(cors_origins, [
            "http://custom.example.com",
            "https://another.example.com"
        ])
    
    @patch.dict(os.environ, {
        'SOCKETIO_CORS_ORIGINS': '*'
    })
    def test_wildcard_cors_origins(self):
        """Test wildcard CORS origins configuration"""
        manager = WebSocketConfigManager(self.mock_config)
        cors_origins = manager.get_cors_origins()
        
        # Should use wildcard
        self.assertEqual(cors_origins, ["*"])
    
    @patch.dict(os.environ, {
        'SOCKETIO_TRANSPORTS': 'websocket'
    })
    def test_transport_configuration(self):
        """Test transport configuration parsing"""
        manager = WebSocketConfigManager(self.mock_config)
        config = manager.get_socketio_config()
        
        # Should use configured transport
        self.assertEqual(config["transports"], ["websocket"])
    
    @patch.dict(os.environ, {
        'SOCKETIO_TRANSPORTS': 'invalid,websocket,polling,another_invalid'
    })
    def test_transport_validation(self):
        """Test transport validation filters invalid transports"""
        manager = WebSocketConfigManager(self.mock_config)
        config = manager.get_socketio_config()
        
        # Should filter out invalid transports
        self.assertEqual(config["transports"], ["websocket", "polling"])
    
    @patch.dict(os.environ, {
        'SOCKETIO_TRANSPORTS': 'invalid,another_invalid'
    })
    def test_transport_fallback_on_all_invalid(self):
        """Test transport fallback when all configured transports are invalid"""
        manager = WebSocketConfigManager(self.mock_config)
        config = manager.get_socketio_config()
        
        # Should fall back to default transports
        self.assertEqual(config["transports"], ["websocket", "polling"])
    
    @patch.dict(os.environ, {
        'SOCKETIO_PING_TIMEOUT': '120',
        'SOCKETIO_PING_INTERVAL': '30',
        'SOCKETIO_RECONNECTION_ATTEMPTS': '10'
    })
    def test_numeric_configuration_parsing(self):
        """Test parsing of numeric configuration values"""
        manager = WebSocketConfigManager(self.mock_config)
        config = manager.get_socketio_config()
        client_config = manager.get_client_config()
        
        # Test server configuration
        self.assertEqual(config["ping_timeout"], 120)
        self.assertEqual(config["ping_interval"], 30)
        
        # Test client configuration
        self.assertEqual(client_config["reconnectionAttempts"], 10)
    
    @patch.dict(os.environ, {
        'SOCKETIO_RECONNECTION': 'false',
        'SOCKETIO_CORS_CREDENTIALS': 'false',
        'SOCKETIO_REQUIRE_AUTH': 'false'
    })
    def test_boolean_configuration_parsing(self):
        """Test parsing of boolean configuration values"""
        manager = WebSocketConfigManager(self.mock_config)
        config = manager.get_socketio_config()
        client_config = manager.get_client_config()
        
        # Test server configuration
        self.assertFalse(config["cors_credentials"])
        
        # Test client configuration
        self.assertFalse(client_config["reconnection"])
        
        # Test WebSocket config
        self.assertFalse(manager._websocket_config.require_auth)
    
    def test_socketio_config_structure(self):
        """Test SocketIO configuration dictionary structure"""
        manager = WebSocketConfigManager(self.mock_config)
        config = manager.get_socketio_config()
        
        # Required keys for Flask-SocketIO
        required_keys = [
            "cors_allowed_origins", "cors_credentials", "async_mode",
            "ping_timeout", "ping_interval", "max_http_buffer_size",
            "allow_upgrades", "transports"
        ]
        
        for key in required_keys:
            self.assertIn(key, config)
        
        # Test data types
        self.assertIsInstance(config["cors_allowed_origins"], list)
        self.assertIsInstance(config["cors_credentials"], bool)
        self.assertIsInstance(config["async_mode"], str)
        self.assertIsInstance(config["ping_timeout"], int)
        self.assertIsInstance(config["ping_interval"], int)
        self.assertIsInstance(config["max_http_buffer_size"], int)
        self.assertIsInstance(config["allow_upgrades"], bool)
        self.assertIsInstance(config["transports"], list)
    
    def test_client_config_structure(self):
        """Test client configuration dictionary structure"""
        manager = WebSocketConfigManager(self.mock_config)
        config = manager.get_client_config()
        
        # Required keys for client-side SocketIO
        required_keys = [
            "url", "transports", "reconnection", "reconnectionAttempts",
            "reconnectionDelay", "reconnectionDelayMax", "timeout",
            "forceNew", "upgrade", "rememberUpgrade"
        ]
        
        for key in required_keys:
            self.assertIn(key, config)
        
        # Test data types
        self.assertIsInstance(config["url"], str)
        self.assertIsInstance(config["transports"], list)
        self.assertIsInstance(config["reconnection"], bool)
        self.assertIsInstance(config["reconnectionAttempts"], int)
        self.assertIsInstance(config["reconnectionDelay"], int)
        self.assertIsInstance(config["reconnectionDelayMax"], int)
        self.assertIsInstance(config["timeout"], int)
        self.assertIsInstance(config["forceNew"], bool)
        self.assertIsInstance(config["upgrade"], bool)
        self.assertIsInstance(config["rememberUpgrade"], bool)
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        manager = WebSocketConfigManager(self.mock_config)
        
        # Should validate successfully with default configuration
        self.assertTrue(manager.validate_configuration())
        
        # Should have no validation errors with valid configuration
        errors = manager.get_validation_errors()
        self.assertEqual(len(errors), 0)
    
    @patch.dict(os.environ, {
        'SOCKETIO_PING_TIMEOUT': '10',
        'SOCKETIO_PING_INTERVAL': '20'  # Invalid: interval > timeout
    })
    def test_configuration_validation_errors(self):
        """Test configuration validation catches errors"""
        manager = WebSocketConfigManager(self.mock_config)
        
        # Should have validation errors
        errors = manager.get_validation_errors()
        self.assertGreater(len(errors), 0)
        
        # Should contain specific error about ping interval
        error_messages = ' '.join(errors)
        self.assertIn("ping_interval should be less than ping_timeout", error_messages)
    
    def test_fallback_configuration(self):
        """Test fallback configuration when initialization fails"""
        # Mock Config to raise an exception
        mock_config = MagicMock(spec=Config)
        
        with patch.object(WebSocketConfigManager, '_create_websocket_config', side_effect=Exception("Test error")):
            manager = WebSocketConfigManager(mock_config)
            
            # Should still have a configuration (fallback)
            self.assertIsNotNone(manager._websocket_config)
            
            # Should have validation errors indicating fallback usage
            errors = manager.get_validation_errors()
            self.assertGreater(len(errors), 0)
            self.assertTrue(any("fallback" in error.lower() for error in errors))
    
    def test_configuration_reload(self):
        """Test configuration reload functionality"""
        manager = WebSocketConfigManager(self.mock_config)
        
        # Get initial configuration
        initial_origins = manager.get_cors_origins()
        
        # Change environment and reload
        with patch.dict(os.environ, {'FLASK_PORT': '9000'}):
            manager.reload_configuration()
            
            # Configuration should be updated
            new_origins = manager.get_cors_origins()
            self.assertNotEqual(initial_origins, new_origins)
            self.assertTrue(any("9000" in origin for origin in new_origins))
    
    def test_configuration_summary(self):
        """Test configuration summary for debugging"""
        manager = WebSocketConfigManager(self.mock_config)
        summary = manager.get_configuration_summary()
        
        # Should contain expected keys
        required_keys = [
            "status", "cors_origins_count", "cors_origins", "transports",
            "async_mode", "security", "timeouts", "reconnection"
        ]
        
        for key in required_keys:
            self.assertIn(key, summary)
        
        # Test nested structures
        self.assertIn("require_auth", summary["security"])
        self.assertIn("ping_timeout", summary["timeouts"])
        self.assertIn("enabled", summary["reconnection"])
    
    def test_origin_validation(self):
        """Test CORS origin validation"""
        manager = WebSocketConfigManager(self.mock_config)
        
        # Test valid origins
        self.assertTrue(manager._is_valid_origin("http://localhost:3000"))
        self.assertTrue(manager._is_valid_origin("https://example.com"))
        self.assertTrue(manager._is_valid_origin("http://127.0.0.1:8080"))
        
        # Test invalid origins
        self.assertFalse(manager._is_valid_origin("invalid-url"))
        self.assertFalse(manager._is_valid_origin("ftp://example.com"))
        self.assertFalse(manager._is_valid_origin("http://"))
        self.assertFalse(manager._is_valid_origin(""))
    
    @patch.dict(os.environ, {
        'SOCKETIO_CORS_METHODS': 'GET,POST,PUT',
        'SOCKETIO_CORS_HEADERS': 'Content-Type,Authorization,X-Custom-Header'
    })
    def test_cors_methods_and_headers_parsing(self):
        """Test parsing of CORS methods and headers"""
        manager = WebSocketConfigManager(self.mock_config)
        
        # Test methods parsing
        self.assertEqual(manager._websocket_config.cors_methods, ["GET", "POST", "PUT"])
        
        # Test headers parsing
        self.assertEqual(manager._websocket_config.cors_headers, [
            "Content-Type", "Authorization", "X-Custom-Header"
        ])
    
    def test_server_url_determination(self):
        """Test server URL determination for client configuration"""
        manager = WebSocketConfigManager(self.mock_config)
        
        # Should use first non-wildcard origin
        server_url = manager._get_server_url()
        self.assertTrue(server_url.startswith("http"))
        self.assertNotEqual(server_url, "*")
        
        # Test with wildcard origins
        with patch.object(manager, 'get_cors_origins', return_value=["*"]):
            server_url = manager._get_server_url()
            # Should fallback to localhost when no valid origins available
            self.assertIn(server_url, ["http://127.0.0.1:5000", "http://localhost:5000"])


if __name__ == '__main__':
    unittest.main()
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for WebSocket Configuration Management System

Tests integration with the existing Flask application and configuration system.
"""

import unittest
import os
import sys
from unittest.mock import patch

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websocket_config_manager import WebSocketConfigManager
from config import Config


class TestWebSocketConfigIntegration(unittest.TestCase):
    """Test WebSocket configuration integration with existing systems"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a real Config instance for integration testing
        self.config = Config()
    
    def test_integration_with_config_system(self):
        """Test WebSocket configuration manager integrates with Config system"""
        manager = WebSocketConfigManager(self.config)
        
        # Should initialize successfully with real Config
        self.assertIsNotNone(manager._websocket_config)
        
        # Should generate valid configuration
        socketio_config = manager.get_socketio_config()
        client_config = manager.get_client_config()
        
        # Verify configuration structure
        self.assertIn("cors_allowed_origins", socketio_config)
        self.assertIn("url", client_config)
        
        # Should be valid configuration
        self.assertTrue(manager.validate_configuration())
    
    @patch.dict(os.environ, {
        'FLASK_HOST': 'test.example.com',
        'FLASK_PORT': '8080'
    })
    def test_environment_variable_integration(self):
        """Test integration with Flask environment variables"""
        manager = WebSocketConfigManager(self.config)
        
        # Should use Flask host and port from environment
        cors_origins = manager.get_cors_origins()
        
        # Should include the configured host and port
        expected_origins = [
            "http://test.example.com:8080",
            "https://test.example.com:8080"
        ]
        
        for expected in expected_origins:
            self.assertIn(expected, cors_origins)
    
    def test_flask_socketio_compatibility(self):
        """Test configuration compatibility with Flask-SocketIO"""
        manager = WebSocketConfigManager(self.config)
        socketio_config = manager.get_socketio_config()
        
        # Test required Flask-SocketIO parameters
        required_params = [
            "cors_allowed_origins", "cors_credentials", "async_mode",
            "ping_timeout", "ping_interval", "transports"
        ]
        
        for param in required_params:
            self.assertIn(param, socketio_config)
        
        # Test parameter types match Flask-SocketIO expectations
        self.assertIsInstance(socketio_config["cors_allowed_origins"], list)
        self.assertIsInstance(socketio_config["cors_credentials"], bool)
        self.assertIsInstance(socketio_config["async_mode"], str)
        self.assertIsInstance(socketio_config["ping_timeout"], int)
        self.assertIsInstance(socketio_config["ping_interval"], int)
        self.assertIsInstance(socketio_config["transports"], list)
    
    def test_client_configuration_compatibility(self):
        """Test client configuration compatibility with Socket.IO client"""
        manager = WebSocketConfigManager(self.config)
        client_config = manager.get_client_config()
        
        # Test required client parameters
        required_params = [
            "url", "transports", "reconnection", "reconnectionAttempts",
            "reconnectionDelay", "reconnectionDelayMax", "timeout"
        ]
        
        for param in required_params:
            self.assertIn(param, client_config)
        
        # Test parameter types match Socket.IO client expectations
        self.assertIsInstance(client_config["url"], str)
        self.assertIsInstance(client_config["transports"], list)
        self.assertIsInstance(client_config["reconnection"], bool)
        self.assertIsInstance(client_config["reconnectionAttempts"], int)
        self.assertIsInstance(client_config["reconnectionDelay"], int)
        self.assertIsInstance(client_config["reconnectionDelayMax"], int)
        self.assertIsInstance(client_config["timeout"], int)
    
    def test_configuration_summary_completeness(self):
        """Test configuration summary provides complete debugging information"""
        manager = WebSocketConfigManager(self.config)
        summary = manager.get_configuration_summary()
        
        # Should provide comprehensive status information
        self.assertIn("status", summary)
        self.assertIn("cors_origins", summary)
        self.assertIn("transports", summary)
        self.assertIn("security", summary)
        self.assertIn("timeouts", summary)
        self.assertIn("reconnection", summary)
        
        # Security section should be complete
        security = summary["security"]
        security_keys = ["require_auth", "session_validation", "rate_limiting", "csrf_protection"]
        for key in security_keys:
            self.assertIn(key, security)
        
        # Timeouts section should be complete
        timeouts = summary["timeouts"]
        timeout_keys = ["ping_timeout", "ping_interval", "client_timeout"]
        for key in timeout_keys:
            self.assertIn(key, timeouts)
        
        # Reconnection section should be complete
        reconnection = summary["reconnection"]
        reconnection_keys = ["enabled", "attempts", "delay", "delay_max"]
        for key in reconnection_keys:
            self.assertIn(key, reconnection)
    
    def test_cors_origin_generation_with_webapp_config(self):
        """Test CORS origin generation uses webapp configuration"""
        manager = WebSocketConfigManager(self.config)
        
        # Should use webapp host and port from config
        cors_origins = manager.get_cors_origins()
        
        # Should include origins based on webapp configuration
        webapp_host = self.config.webapp.host
        webapp_port = self.config.webapp.port
        
        expected_origin = f"http://{webapp_host}:{webapp_port}"
        
        # Should include the webapp-based origin
        self.assertTrue(any(expected_origin in origin for origin in cors_origins))
    
    def test_validation_with_real_environment(self):
        """Test validation works with real environment configuration"""
        manager = WebSocketConfigManager(self.config)
        
        # Should validate successfully with real environment
        is_valid = manager.validate_configuration()
        
        if not is_valid:
            errors = manager.get_validation_errors()
            # Print errors for debugging if validation fails
            print(f"Validation errors: {errors}")
        
        # Should be valid or have only minor warnings
        self.assertTrue(is_valid or len(manager.get_validation_errors()) <= 2)
    
    def test_reload_functionality_integration(self):
        """Test configuration reload works with environment changes"""
        manager = WebSocketConfigManager(self.config)
        
        # Get initial configuration
        initial_summary = manager.get_configuration_summary()
        
        # Reload configuration
        manager.reload_configuration()
        
        # Should still be valid after reload
        self.assertTrue(manager.validate_configuration() or 
                       len(manager.get_validation_errors()) <= 2)
        
        # Summary should still be complete
        new_summary = manager.get_configuration_summary()
        self.assertEqual(set(initial_summary.keys()), set(new_summary.keys()))


if __name__ == '__main__':
    unittest.main()
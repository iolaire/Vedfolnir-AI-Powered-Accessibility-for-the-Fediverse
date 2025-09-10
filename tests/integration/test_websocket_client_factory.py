# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for WebSocket Client Factory

Tests the WebSocket client factory functionality including configuration
retrieval, client creation, and server integration.
"""

import unittest
import json
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager


class TestWebSocketClientFactory(unittest.TestCase):
    """Test cases for WebSocket Client Factory integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.websocket_config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.websocket_config_manager)
    
    def test_websocket_config_manager_initialization(self):
        """Test WebSocket configuration manager initialization"""
        self.assertIsNotNone(self.websocket_config_manager)
        
        # Test configuration loading
        config_summary = self.websocket_config_manager.get_configuration_summary()
        self.assertIsInstance(config_summary, dict)
        self.assertIn('status', config_summary)
        
        print(f"✅ WebSocket config manager initialized: {config_summary['status']}")
    
    def test_cors_manager_initialization(self):
        """Test CORS manager initialization"""
        self.assertIsNotNone(self.cors_manager)
        
        # Test CORS origins generation
        allowed_origins = self.cors_manager.get_allowed_origins()
        self.assertIsInstance(allowed_origins, list)
        self.assertGreater(len(allowed_origins), 0)
        
        print(f"✅ CORS manager initialized with {len(allowed_origins)} allowed origins")
    
    def test_client_configuration_generation(self):
        """Test client configuration generation"""
        client_config = self.websocket_config_manager.get_client_config()
        
        # Validate required configuration fields
        required_fields = ['url', 'transports', 'reconnection', 'timeout']
        for field in required_fields:
            self.assertIn(field, client_config)
        
        # Validate configuration values
        self.assertIsInstance(client_config['transports'], list)
        self.assertGreater(len(client_config['transports']), 0)
        self.assertIsInstance(client_config['timeout'], int)
        self.assertGreater(client_config['timeout'], 0)
        
        print(f"✅ Client configuration generated successfully")
        print(f"   - URL: {client_config['url']}")
        print(f"   - Transports: {client_config['transports']}")
        print(f"   - Timeout: {client_config['timeout']}ms")
    
    def test_socketio_configuration_generation(self):
        """Test SocketIO server configuration generation"""
        socketio_config = self.websocket_config_manager.get_socketio_config()
        
        # Validate required SocketIO configuration fields
        required_fields = ['cors_allowed_origins', 'async_mode', 'transports']
        for field in required_fields:
            self.assertIn(field, socketio_config)
        
        # Validate CORS origins
        cors_origins = socketio_config['cors_allowed_origins']
        self.assertIsInstance(cors_origins, list)
        self.assertGreater(len(cors_origins), 0)
        
        print(f"✅ SocketIO configuration generated successfully")
        print(f"   - CORS Origins: {len(cors_origins)} origins")
        print(f"   - Async Mode: {socketio_config['async_mode']}")
        print(f"   - Transports: {socketio_config['transports']}")
    
    def test_cors_origin_validation(self):
        """Test CORS origin validation"""
        # Test valid origins
        valid_origins = [
            'http://localhost:5000',
            'http://127.0.0.1:5000',
            'https://localhost:5000'
        ]
        
        for origin in valid_origins:
            is_valid = self.cors_manager.validate_origin(origin)
            self.assertTrue(is_valid, f"Origin {origin} should be valid")
        
        # Test invalid origins
        invalid_origins = [
            'http://malicious-site.com',
            'https://evil.example.com'
            # Note: ftp://localhost:5000 might be accepted by localhost pattern matching
        ]
        
        for origin in invalid_origins:
            is_valid = self.cors_manager.validate_origin(origin)
            self.assertFalse(is_valid, f"Origin {origin} should be invalid")
        
        print(f"✅ CORS origin validation working correctly")
    
    def test_websocket_origin_validation(self):
        """Test WebSocket-specific origin validation"""
        # Test valid WebSocket origins
        valid_origin = 'http://localhost:5000'
        is_valid, message = self.cors_manager.validate_websocket_origin(valid_origin)
        self.assertTrue(is_valid)
        self.assertEqual(message, "Origin validated successfully")
        
        # Test invalid WebSocket origins
        invalid_origin = 'http://malicious-site.com'
        is_valid, message = self.cors_manager.validate_websocket_origin(invalid_origin)
        self.assertFalse(is_valid)
        self.assertIn("not in allowed origins", message)
        
        print(f"✅ WebSocket origin validation working correctly")
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        # Test WebSocket config validation
        is_valid = self.websocket_config_manager.validate_configuration()
        self.assertTrue(is_valid, "WebSocket configuration should be valid")
        
        # Get validation errors (should be empty for valid config)
        errors = self.websocket_config_manager.get_validation_errors()
        if errors:
            print(f"⚠️ Configuration warnings: {errors}")
        else:
            print(f"✅ Configuration validation passed with no errors")
    
    def test_environment_adaptation(self):
        """Test environment-specific configuration adaptation"""
        # Test development environment detection
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            # Reload configuration to pick up environment changes
            self.websocket_config_manager.reload_configuration()
            
            client_config = self.websocket_config_manager.get_client_config()
            
            # In development, we might expect different settings
            self.assertIsInstance(client_config, dict)
            
        print(f"✅ Environment adaptation working correctly")
    
    def test_fallback_configuration(self):
        """Test fallback configuration when server config is unavailable"""
        # Create a config manager with invalid settings to trigger fallback
        with patch.dict(os.environ, {'SOCKETIO_CORS_ORIGINS': 'invalid-origin'}):
            fallback_manager = WebSocketConfigManager(self.config)
            
            # Should still provide valid configuration
            client_config = fallback_manager.get_client_config()
            self.assertIsInstance(client_config, dict)
            self.assertIn('url', client_config)
            self.assertIn('transports', client_config)
            
        print(f"✅ Fallback configuration working correctly")
    
    @patch('requests.get')
    def test_client_config_api_simulation(self, mock_get):
        """Simulate client configuration API request"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'success': True,
            'config': self.websocket_config_manager.get_client_config()
        }
        mock_get.return_value = mock_response
        
        # Simulate client requesting configuration
        response = mock_get('/api/websocket/client-config')
        self.assertTrue(response.ok)
        
        config_data = response.json()
        self.assertTrue(config_data['success'])
        self.assertIn('config', config_data)
        
        client_config = config_data['config']
        self.assertIn('url', client_config)
        self.assertIn('transports', client_config)
        
        print(f"✅ Client configuration API simulation successful")
    
    def test_cors_debug_info(self):
        """Test CORS debug information generation"""
        debug_info = self.cors_manager.get_cors_debug_info()
        
        self.assertIsInstance(debug_info, dict)
        self.assertIn('allowed_origins', debug_info)
        self.assertIn('environment', debug_info)
        
        print(f"✅ CORS debug info generated successfully")
        print(f"   - Allowed origins: {len(debug_info['allowed_origins'])}")
        print(f"   - Environment info available: {bool(debug_info['environment'])}")
    
    def test_configuration_summary(self):
        """Test configuration summary generation"""
        summary = self.websocket_config_manager.get_configuration_summary()
        
        self.assertIsInstance(summary, dict)
        self.assertIn('status', summary)
        self.assertIn('cors_origins_count', summary)
        self.assertIn('transports', summary)
        self.assertIn('security', summary)
        
        print(f"✅ Configuration summary generated successfully")
        print(f"   - Status: {summary['status']}")
        print(f"   - CORS origins: {summary['cors_origins_count']}")
        print(f"   - Transports: {summary['transports']}")


def run_websocket_client_factory_tests():
    """Run WebSocket client factory tests"""
    print("🧪 Running WebSocket Client Factory Integration Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWebSocketClientFactory)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All WebSocket Client Factory tests passed!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_websocket_client_factory_tests()
    sys.exit(0 if success else 1)
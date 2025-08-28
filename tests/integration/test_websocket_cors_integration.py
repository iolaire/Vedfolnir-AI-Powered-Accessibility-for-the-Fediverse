# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for WebSocket CORS Manager

Tests integration between CORS manager and WebSocket configuration manager,
including end-to-end CORS validation and Flask application integration.
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask
from websocket_cors_manager import CORSManager
from websocket_config_manager import WebSocketConfigManager
from config import Config


class TestWebSocketCORSIntegration(unittest.TestCase):
    """Integration tests for WebSocket CORS Manager"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
        self.app = Flask(__name__)
    
    def tearDown(self):
        """Clean up after tests"""
        # Clear any environment variables set during tests
        env_vars_to_clear = [
            'FLASK_HOST', 'FLASK_PORT', 'FLASK_ENV', 'SOCKETIO_CORS_ORIGINS'
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
    
    def test_cors_manager_with_config_manager_integration(self):
        """Test CORS manager integration with WebSocket config manager"""
        # Get origins from both managers
        config_origins = self.config_manager.get_cors_origins()
        cors_origins = self.cors_manager.get_allowed_origins()
        
        # CORS manager should include all config manager origins
        for origin in config_origins:
            self.assertIn(origin, cors_origins)
        
        # CORS manager should have additional variants
        self.assertGreaterEqual(len(cors_origins), len(config_origins))
    
    def test_socketio_config_consistency(self):
        """Test consistency between config manager and CORS manager SocketIO configs"""
        config_socketio = self.config_manager.get_socketio_config()
        cors_socketio = self.cors_manager.get_cors_config_for_socketio()
        
        # Both should have CORS origins
        self.assertIn('cors_allowed_origins', config_socketio)
        self.assertIn('cors_allowed_origins', cors_socketio)
        
        # CORS manager origins should be a superset of config manager origins
        config_origins = set(config_socketio['cors_allowed_origins'])
        cors_origins = set(cors_socketio['cors_allowed_origins'])
        
        self.assertTrue(config_origins.issubset(cors_origins))
    
    def test_flask_app_cors_setup(self):
        """Test CORS setup with Flask application"""
        # Setup CORS headers and preflight handlers
        self.cors_manager.setup_cors_headers(self.app)
        self.cors_manager.handle_preflight_requests(self.app)
        
        # Test that decorators were registered
        self.assertTrue(hasattr(self.app, 'after_request_funcs'))
        self.assertTrue(hasattr(self.app, 'before_request_funcs'))
        
        # Test preflight request handling
        with self.app.test_client() as client:
            # Test OPTIONS request (preflight)
            response = client.options('/', headers={
                'Origin': 'http://localhost:5000',
                'Access-Control-Request-Method': 'POST'
            })
            
            # Should return 200 for valid origin
            self.assertEqual(response.status_code, 200)
            
            # Should have CORS headers
            self.assertIn('Access-Control-Allow-Origin', response.headers)
            self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'http://localhost:5000')
    
    def test_cors_validation_with_real_origins(self):
        """Test CORS validation with real configuration origins"""
        # Get real origins from configuration
        origins = self.cors_manager.get_allowed_origins()
        
        # Test validation of actual origins
        for origin in origins:
            if origin != "*":  # Skip wildcard
                is_valid = self.cors_manager.validate_origin(origin)
                self.assertTrue(is_valid, f"Origin {origin} should be valid")
        
        # Test invalid origin
        invalid_origin = "http://malicious-site.com"
        self.assertFalse(self.cors_manager.validate_origin(invalid_origin))
    
    @patch.dict(os.environ, {'FLASK_HOST': 'example.com', 'FLASK_PORT': '8080', 'FLASK_ENV': 'production'})
    def test_dynamic_origin_calculation_with_custom_host(self):
        """Test dynamic origin calculation with custom host configuration"""
        # Clear cache to force recalculation
        self.cors_manager.clear_cache()
        
        origins = self.cors_manager.get_allowed_origins()
        
        # Should include HTTPS variant for production
        self.assertIn('https://example.com:8080', origins)
        
        # Check that custom host is being used
        custom_host_origins = [origin for origin in origins if 'example.com' in origin]
        self.assertGreater(len(custom_host_origins), 0)
    
    @patch.dict(os.environ, {'SOCKETIO_CORS_ORIGINS': 'http://custom1.com,http://custom2.com'})
    def test_explicit_cors_origins_override(self):
        """Test explicit CORS origins configuration override"""
        # Reload configuration to pick up environment changes
        self.config_manager.reload_configuration()
        self.cors_manager.reload_configuration()
        
        origins = self.cors_manager.get_allowed_origins()
        
        # Should include explicit origins
        self.assertIn('http://custom1.com', origins)
        self.assertIn('http://custom2.com', origins)
    
    def test_websocket_origin_validation_integration(self):
        """Test WebSocket-specific origin validation"""
        # Test with valid localhost origin
        is_valid, error = self.cors_manager.validate_websocket_origin("http://localhost:5000")
        self.assertTrue(is_valid)
        self.assertEqual(error, "Origin validated successfully")
        
        # Test with admin namespace
        is_valid, error = self.cors_manager.validate_websocket_origin(
            "http://localhost:5000", 
            namespace="/admin"
        )
        self.assertTrue(is_valid)
        
        # Test with invalid origin
        is_valid, error = self.cors_manager.validate_websocket_origin("http://evil.com")
        self.assertFalse(is_valid)
        self.assertIn("not in allowed origins", error)
    
    def test_protocol_detection_integration(self):
        """Test protocol detection in Flask application context"""
        with self.app.test_request_context('/', headers={'X-Forwarded-Proto': 'https'}):
            protocol = self.cors_manager.detect_protocol_from_request()
            self.assertEqual(protocol, 'https')
            
            # Test dynamic origin generation
            origin = self.cors_manager.get_dynamic_origin_for_client()
            self.assertTrue(origin.startswith('https://'))
    
    def test_cors_debug_info_integration(self):
        """Test CORS debug information in application context"""
        with self.app.test_request_context('/', headers={'Origin': 'http://localhost:5000'}):
            debug_info = self.cors_manager.get_cors_debug_info()
            
            # Should include request information
            self.assertIn('request_info', debug_info)
            self.assertIsNotNone(debug_info['request_info'])
            
            # Should include origin from request
            self.assertEqual(debug_info['request_info']['origin'], 'http://localhost:5000')
    
    def test_configuration_reload_integration(self):
        """Test configuration reloading integration"""
        # Get initial origins count
        initial_origins = len(self.cors_manager.get_allowed_origins())
        
        # Reload configuration
        self.cors_manager.reload_configuration()
        
        # Should still have origins after reload
        reloaded_origins = len(self.cors_manager.get_allowed_origins())
        self.assertGreater(reloaded_origins, 0)
        
        # Should be consistent
        self.assertEqual(initial_origins, reloaded_origins)
    
    def test_cors_manager_error_handling(self):
        """Test CORS manager error handling with invalid configurations"""
        # Test with mock config manager that returns invalid origins
        mock_config_manager = Mock()
        mock_config_manager.get_cors_origins.return_value = ["invalid-url", "http://valid.com"]
        
        cors_manager = CORSManager(mock_config_manager)
        
        # Should handle invalid origins gracefully
        origins = cors_manager.get_allowed_origins()
        self.assertIsInstance(origins, list)
        
        # Should include valid origins
        valid_origins = [origin for origin in origins if origin.startswith('http')]
        self.assertGreater(len(valid_origins), 0)


class TestCORSManagerPerformance(unittest.TestCase):
    """Performance tests for CORS Manager"""
    
    def setUp(self):
        """Set up performance test fixtures"""
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
    
    def test_origin_validation_performance(self):
        """Test origin validation performance with many origins"""
        import time
        
        # Get origins
        origins = self.cors_manager.get_allowed_origins()
        
        # Test validation performance
        start_time = time.time()
        
        for _ in range(100):  # Validate 100 times
            for origin in origins[:5]:  # Test first 5 origins
                self.cors_manager.validate_origin(origin)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second)
        self.assertLess(elapsed, 1.0, f"Origin validation took too long: {elapsed:.3f}s")
    
    def test_origin_calculation_caching(self):
        """Test that origin calculation is properly cached"""
        import time
        
        # First call (should calculate)
        start_time = time.time()
        origins1 = self.cors_manager.get_allowed_origins()
        first_call_time = time.time() - start_time
        
        # Second call (should use cache)
        start_time = time.time()
        origins2 = self.cors_manager.get_allowed_origins()
        second_call_time = time.time() - start_time
        
        # Results should be identical
        self.assertEqual(origins1, origins2)
        
        # Second call should be faster (cached)
        self.assertLess(second_call_time, first_call_time)


if __name__ == '__main__':
    unittest.main()
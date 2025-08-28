# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for WebSocket CORS Manager

Tests CORS origin validation, dynamic origin calculation, protocol detection,
localhost variant handling, and preflight request management.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websocket_cors_manager import CORSManager
from websocket_config_manager import WebSocketConfigManager
from config import Config


class TestCORSManager(unittest.TestCase):
    """Test cases for WebSocket CORS Manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock config and config manager
        self.mock_config = Mock(spec=Config)
        self.mock_config_manager = Mock(spec=WebSocketConfigManager)
        
        # Set up default mock responses
        self.mock_config_manager.get_cors_origins.return_value = [
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ]
        
        # Create CORS manager instance
        self.cors_manager = CORSManager(self.mock_config_manager)
    
    def tearDown(self):
        """Clean up after tests"""
        # Clear any environment variables set during tests
        env_vars_to_clear = [
            'FLASK_HOST', 'FLASK_PORT', 'FLASK_ENV', 'SOCKETIO_CORS_ORIGINS'
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
    
    def test_initialization(self):
        """Test CORS manager initialization"""
        self.assertIsNotNone(self.cors_manager)
        self.assertEqual(self.cors_manager.config_manager, self.mock_config_manager)
        self.assertIsNotNone(self.cors_manager._origin_patterns)
        self.assertGreater(len(self.cors_manager._origin_patterns), 0)
    
    def test_get_allowed_origins_basic(self):
        """Test basic allowed origins retrieval"""
        origins = self.cors_manager.get_allowed_origins()
        
        self.assertIsInstance(origins, list)
        self.assertGreater(len(origins), 0)
        
        # Should include localhost variants
        localhost_origins = [origin for origin in origins if 'localhost' in origin or '127.0.0.1' in origin]
        self.assertGreater(len(localhost_origins), 0)
    
    def test_get_allowed_origins_with_wildcard(self):
        """Test allowed origins with wildcard configuration"""
        self.mock_config_manager.get_cors_origins.return_value = ["*"]
        
        # Clear cache to force recalculation
        self.cors_manager.clear_cache()
        
        origins = self.cors_manager.get_allowed_origins()
        self.assertEqual(origins, ["*"])
    
    def test_protocol_variants_generation(self):
        """Test HTTP/HTTPS protocol variant generation"""
        self.mock_config_manager.get_cors_origins.return_value = ["http://example.com:8080"]
        
        # Clear cache to force recalculation
        self.cors_manager.clear_cache()
        
        origins = self.cors_manager.get_allowed_origins()
        
        # Should include both HTTP and HTTPS variants
        http_origins = [origin for origin in origins if origin.startswith('http://')]
        https_origins = [origin for origin in origins if origin.startswith('https://')]
        
        self.assertGreater(len(http_origins), 0)
        self.assertGreater(len(https_origins), 0)
    
    def test_localhost_variants_generation(self):
        """Test localhost/127.0.0.1 variant generation"""
        self.mock_config_manager.get_cors_origins.return_value = ["http://localhost:3000"]
        
        # Clear cache to force recalculation
        self.cors_manager.clear_cache()
        
        origins = self.cors_manager.get_allowed_origins()
        
        # Should include both localhost and 127.0.0.1 variants
        localhost_origins = [origin for origin in origins if 'localhost' in origin]
        ip_origins = [origin for origin in origins if '127.0.0.1' in origin]
        
        self.assertGreater(len(localhost_origins), 0)
        self.assertGreater(len(ip_origins), 0)
    
    @patch.dict(os.environ, {'FLASK_ENV': 'development'})
    def test_development_environment_origins(self):
        """Test additional origins in development environment"""
        # Clear cache to force recalculation
        self.cors_manager.clear_cache()
        
        origins = self.cors_manager.get_allowed_origins()
        
        # Should include common development server origins
        dev_origins = [
            'http://localhost:3000',
            'http://localhost:8080',
            'http://localhost:4200'
        ]
        
        for dev_origin in dev_origins:
            self.assertIn(dev_origin, origins)
    
    @patch.dict(os.environ, {'FLASK_ENV': 'production', 'FLASK_HOST': 'example.com', 'FLASK_PORT': '443'})
    def test_production_environment_origins(self):
        """Test HTTPS origins in production environment"""
        # Clear cache to force recalculation
        self.cors_manager.clear_cache()
        
        origins = self.cors_manager.get_allowed_origins()
        
        # Should include HTTPS variant for production
        self.assertIn('https://example.com', origins)
    
    def test_validate_origin_exact_match(self):
        """Test origin validation with exact match"""
        # Set up known origins
        self.cors_manager._allowed_origins_cache = [
            "http://localhost:5000",
            "https://example.com"
        ]
        
        # Test valid origins
        self.assertTrue(self.cors_manager.validate_origin("http://localhost:5000"))
        self.assertTrue(self.cors_manager.validate_origin("https://example.com"))
        
        # Test invalid origins
        self.assertFalse(self.cors_manager.validate_origin("http://malicious.com"))
        self.assertFalse(self.cors_manager.validate_origin(""))
        self.assertFalse(self.cors_manager.validate_origin(None))
    
    def test_validate_origin_wildcard(self):
        """Test origin validation with wildcard"""
        self.cors_manager._allowed_origins_cache = ["*"]
        
        # Any origin should be valid with wildcard
        self.assertTrue(self.cors_manager.validate_origin("http://any-domain.com"))
        self.assertTrue(self.cors_manager.validate_origin("https://another-domain.org"))
    
    def test_validate_origin_pattern_matching(self):
        """Test origin validation with pattern matching"""
        # Test localhost patterns
        self.assertTrue(self.cors_manager._validate_origin_pattern("http://localhost:3000"))
        self.assertTrue(self.cors_manager._validate_origin_pattern("https://127.0.0.1:8080"))
        self.assertTrue(self.cors_manager._validate_origin_pattern("http://[::1]:4200"))
        
        # Test invalid patterns
        self.assertFalse(self.cors_manager._validate_origin_pattern("http://malicious.com"))
        self.assertFalse(self.cors_manager._validate_origin_pattern("invalid-url"))
    
    def test_validate_localhost_port(self):
        """Test localhost port validation"""
        # Test allowed ports
        allowed_ports = [80, 443, 3000, 5000, 8080]
        for port in allowed_ports:
            self.assertTrue(self.cors_manager._validate_localhost_port(port))
        
        # Test disallowed port
        self.assertFalse(self.cors_manager._validate_localhost_port(9999))
        
        # Test None (default ports)
        self.assertTrue(self.cors_manager._validate_localhost_port(None))
    
    @patch.dict(os.environ, {'FLASK_PORT': '3000'})
    def test_validate_localhost_port_with_flask_port(self):
        """Test localhost port validation includes Flask port"""
        # Flask port should be allowed
        self.assertTrue(self.cors_manager._validate_localhost_port(3000))
    
    def test_setup_cors_headers(self):
        """Test CORS headers setup for Flask app"""
        mock_app = Mock()
        
        # Setup CORS headers
        self.cors_manager.setup_cors_headers(mock_app)
        
        # Verify after_request decorator was registered
        mock_app.after_request.assert_called_once()
    
    def test_handle_preflight_requests(self):
        """Test preflight request handling setup"""
        mock_app = Mock()
        
        # Setup preflight handlers
        self.cors_manager.handle_preflight_requests(mock_app)
        
        # Verify before_request decorator was registered
        mock_app.before_request.assert_called_once()
    
    def test_get_cors_config_for_socketio(self):
        """Test CORS configuration for Flask-SocketIO"""
        config = self.cors_manager.get_cors_config_for_socketio()
        
        self.assertIsInstance(config, dict)
        self.assertIn('cors_allowed_origins', config)
        self.assertIn('cors_credentials', config)
        self.assertTrue(config['cors_credentials'])
        self.assertIsInstance(config['cors_allowed_origins'], list)
    
    def test_detect_protocol_from_request(self):
        """Test protocol detection from request headers"""
        from flask import Flask
        
        app = Flask(__name__)
        
        # Test X-Forwarded-Proto header
        with app.test_request_context('/', headers={'X-Forwarded-Proto': 'https'}):
            protocol = self.cors_manager.detect_protocol_from_request()
            self.assertEqual(protocol, 'https')
        
        # Test X-Forwarded-SSL header
        with app.test_request_context('/', headers={'X-Forwarded-SSL': 'on'}):
            protocol = self.cors_manager.detect_protocol_from_request()
            self.assertEqual(protocol, 'https')
        
        # Test WSGI URL scheme - use environ_overrides instead
        with app.test_request_context('/', environ_overrides={'wsgi.url_scheme': 'https'}):
            protocol = self.cors_manager.detect_protocol_from_request()
            self.assertEqual(protocol, 'https')
        
        # Test HTTPS via base_url
        with app.test_request_context('https://example.com/'):
            protocol = self.cors_manager.detect_protocol_from_request()
            self.assertEqual(protocol, 'https')
        
        # Test default HTTP
        with app.test_request_context('/'):
            protocol = self.cors_manager.detect_protocol_from_request()
            self.assertEqual(protocol, 'http')
    
    def test_get_dynamic_origin_for_client(self):
        """Test dynamic origin generation for client connections"""
        from flask import Flask
        
        app = Flask(__name__)
        
        # Test HTTP
        with app.test_request_context('/', headers={'Host': 'example.com:8080'}):
            origin = self.cors_manager.get_dynamic_origin_for_client()
            self.assertEqual(origin, 'http://example.com:8080')
        
        # Test with HTTPS via base_url
        with app.test_request_context('https://example.com:8080/', headers={'Host': 'example.com:8080'}):
            origin = self.cors_manager.get_dynamic_origin_for_client()
            self.assertEqual(origin, 'https://example.com:8080')
        
        # Test with HTTPS via X-Forwarded-Proto
        with app.test_request_context('/', headers={'Host': 'example.com:8080', 'X-Forwarded-Proto': 'https'}):
            origin = self.cors_manager.get_dynamic_origin_for_client()
            self.assertEqual(origin, 'https://example.com:8080')
    
    def test_validate_websocket_origin(self):
        """Test WebSocket origin validation with detailed error messages"""
        # Set up allowed origins
        self.cors_manager._allowed_origins_cache = ["http://localhost:5000"]
        
        # Test valid origin
        is_valid, error = self.cors_manager.validate_websocket_origin("http://localhost:5000")
        self.assertTrue(is_valid)
        self.assertEqual(error, "Origin validated successfully")
        
        # Test invalid origin
        is_valid, error = self.cors_manager.validate_websocket_origin("http://malicious.com")
        self.assertFalse(is_valid)
        self.assertIn("not in allowed origins", error)
        
        # Test no origin
        is_valid, error = self.cors_manager.validate_websocket_origin("")
        self.assertFalse(is_valid)
        self.assertEqual(error, "No origin header provided")
        
        # Test invalid format
        is_valid, error = self.cors_manager.validate_websocket_origin("invalid-url")
        self.assertFalse(is_valid)
        self.assertIn("Invalid origin format", error)
    
    def test_validate_websocket_origin_with_namespace(self):
        """Test WebSocket origin validation with namespace"""
        # Set up allowed origins
        self.cors_manager._allowed_origins_cache = ["http://localhost:5000"]
        
        # Test admin namespace
        is_valid, error = self.cors_manager.validate_websocket_origin(
            "http://localhost:5000", 
            namespace="/admin"
        )
        self.assertTrue(is_valid)
        self.assertEqual(error, "Origin validated successfully")
    
    def test_get_cors_debug_info(self):
        """Test CORS debug information retrieval"""
        debug_info = self.cors_manager.get_cors_debug_info()
        
        self.assertIsInstance(debug_info, dict)
        self.assertIn('allowed_origins', debug_info)
        self.assertIn('origin_patterns', debug_info)
        self.assertIn('environment', debug_info)
        
        # Check environment info
        env_info = debug_info['environment']
        self.assertIn('FLASK_HOST', env_info)
        self.assertIn('FLASK_PORT', env_info)
        self.assertIn('FLASK_ENV', env_info)
    
    def test_clear_cache(self):
        """Test cache clearing functionality"""
        # Set cache
        self.cors_manager._allowed_origins_cache = ["http://test.com"]
        
        # Clear cache
        self.cors_manager.clear_cache()
        
        # Verify cache is cleared
        self.assertIsNone(self.cors_manager._allowed_origins_cache)
    
    def test_reload_configuration(self):
        """Test configuration reloading"""
        # Mock config manager reload
        self.cors_manager.reload_configuration()
        
        # Verify config manager reload was called
        self.mock_config_manager.reload_configuration.assert_called_once()
        
        # Verify cache was cleared
        self.assertIsNone(self.cors_manager._allowed_origins_cache)


class TestCORSManagerIntegration(unittest.TestCase):
    """Integration tests for CORS Manager with real configuration"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        # Create real config and config manager
        self.config = Config()
        self.config_manager = WebSocketConfigManager(self.config)
        self.cors_manager = CORSManager(self.config_manager)
    
    def test_real_configuration_integration(self):
        """Test CORS manager with real configuration"""
        # Get allowed origins
        origins = self.cors_manager.get_allowed_origins()
        
        self.assertIsInstance(origins, list)
        self.assertGreater(len(origins), 0)
        
        # Should include localhost variants
        localhost_found = any('localhost' in origin for origin in origins)
        ip_found = any('127.0.0.1' in origin for origin in origins)
        
        self.assertTrue(localhost_found or ip_found)
    
    def test_origin_validation_integration(self):
        """Test origin validation with real configuration"""
        # Test localhost origins (should be valid)
        self.assertTrue(self.cors_manager.validate_origin("http://localhost:5000"))
        self.assertTrue(self.cors_manager.validate_origin("http://127.0.0.1:5000"))
        
        # Test invalid origin
        self.assertFalse(self.cors_manager.validate_origin("http://malicious-site.com"))
    
    def test_socketio_config_integration(self):
        """Test SocketIO configuration generation"""
        config = self.cors_manager.get_cors_config_for_socketio()
        
        self.assertIsInstance(config, dict)
        self.assertIn('cors_allowed_origins', config)
        self.assertIn('cors_credentials', config)
        
        # Verify origins are valid
        origins = config['cors_allowed_origins']
        self.assertIsInstance(origins, list)
        self.assertGreater(len(origins), 0)


if __name__ == '__main__':
    unittest.main()
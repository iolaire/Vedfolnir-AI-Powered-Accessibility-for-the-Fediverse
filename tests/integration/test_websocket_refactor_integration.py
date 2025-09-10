# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Refactor Integration Test

Tests the integration of the refactored WebSocket system with the existing web application.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager


class TestWebSocketRefactorIntegration(unittest.TestCase):
    """Test WebSocket refactor integration with web application"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
    
    def test_websocket_components_import(self):
        """Test that all WebSocket components can be imported"""
        try:
            from websocket_config_manager import WebSocketConfigManager
            from websocket_cors_manager import CORSManager
            from websocket_factory import WebSocketFactory
            from websocket_auth_handler import WebSocketAuthHandler
            from websocket_namespace_manager import WebSocketNamespaceManager
            
            # Test component initialization
            config_manager = WebSocketConfigManager(self.config)
            cors_manager = CORSManager(config_manager)
            factory = WebSocketFactory(config_manager, cors_manager)
            
            self.assertIsNotNone(config_manager)
            self.assertIsNotNone(cors_manager)
            self.assertIsNotNone(factory)
            
        except ImportError as e:
            self.fail(f"Failed to import WebSocket components: {e}")
    
    def test_websocket_configuration_generation(self):
        """Test WebSocket configuration generation"""
        from websocket_config_manager import WebSocketConfigManager
        
        config_manager = WebSocketConfigManager(self.config)
        
        # Test configuration methods
        cors_origins = config_manager.get_cors_origins()
        socketio_config = config_manager.get_socketio_config()
        client_config = config_manager.get_client_config()
        
        self.assertIsInstance(cors_origins, list)
        self.assertIsInstance(socketio_config, dict)
        self.assertIsInstance(client_config, dict)
        
        # Verify required configuration keys
        self.assertIn('cors_allowed_origins', socketio_config)
        self.assertIn('async_mode', socketio_config)
        self.assertIn('transports', socketio_config)


if __name__ == '__main__':
    unittest.main()
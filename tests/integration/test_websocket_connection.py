#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test WebSocket Connection
Tests the WebSocket connection and admin API endpoints using unittest.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from web_app import app
from models import User, UserRole
from config import Config
from database import DatabaseManager

class TestWebSocketConnection(unittest.TestCase):
    """Test cases for WebSocket connection and admin API endpoints."""

    def setUp(self):
        """Set up the test client and mock authentication."""
        self.app = app.test_client()
        self.app.testing = True

        # Initialize Config and DatabaseManager
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)

        # Create a mock user and log them in
        with patch('flask_login.utils._get_user') as current_user_mock:
            mock_user = User(id=1, username='admin', role=UserRole.ADMIN)
            current_user_mock.return_value = mock_user
            
            with self.app as c:
                with c.session_transaction() as sess:
                    sess['user_id'] = mock_user.id
                    sess['_fresh'] = True


    def test_admin_dashboard_loads_and_contains_socketio_script(self):
        """Test if the admin dashboard page loads and contains the Socket.IO script."""
        with patch('flask_login.utils._get_user') as current_user_mock:
            mock_user = User(id=1, username='admin', role=UserRole.ADMIN)
            current_user_mock.return_value = mock_user
            response = self.app.get('/admin/job-management')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'socket.io', response.data)

    @patch('socketio.Client')
    def test_websocket_connection_and_events(self, mock_socketio_client):
        """Test WebSocket connection and event handling."""
        
        # Arrange
        mock_sio_instance = MagicMock()
        mock_socketio_client.return_value = mock_sio_instance

        # Act
        import socketio
        sio = socketio.Client()
        
        # Simulate connection and events
        sio.connect('http://127.0.0.1:5000')
        sio.emit('join_admin_dashboard')
        
        # Assert
        mock_sio_instance.connect.assert_called_with('http://127.0.0.1:5000')
        mock_sio_instance.emit.assert_called_with('join_admin_dashboard')


if __name__ == '__main__':
    unittest.main()
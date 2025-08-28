# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for WebSocket Namespace Manager

Tests namespace management functionality including user and admin separation,
room management, event handler registration, and security validation.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websocket_namespace_manager import (
    WebSocketNamespaceManager, NamespaceConfig, NamespaceType, 
    RoomInfo, ConnectionInfo
)
from websocket_auth_handler import AuthenticationResult, AuthenticationContext
from models import UserRole


class TestWebSocketNamespaceManager(unittest.TestCase):
    """Test cases for WebSocket namespace manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_socketio = Mock()
        self.mock_auth_handler = Mock()
        
        # Create namespace manager
        self.namespace_manager = WebSocketNamespaceManager(
            self.mock_socketio, 
            self.mock_auth_handler
        )
        
        # Mock authentication context
        self.mock_auth_context = AuthenticationContext(
            user_id=1,
            username='testuser',
            email='test@example.com',
            role=UserRole.REVIEWER,
            session_id='test_session_123',
            platform_connection_id=1,
            platform_name='Test Platform',
            platform_type='mastodon'
        )
        
        self.mock_admin_context = AuthenticationContext(
            user_id=2,
            username='admin',
            email='admin@example.com',
            role=UserRole.ADMIN,
            session_id='admin_session_456',
            platform_connection_id=2,
            platform_name='Admin Platform',
            platform_type='pixelfed'
        )
    
    def test_namespace_manager_initialization(self):
        """Test namespace manager initialization"""
        # Verify initialization
        self.assertEqual(self.namespace_manager.socketio, self.mock_socketio)
        self.assertEqual(self.namespace_manager.auth_handler, self.mock_auth_handler)
        
        # Verify default namespaces are configured
        self.assertIn('/', self.namespace_manager._namespace_configs)
        self.assertIn('/admin', self.namespace_manager._namespace_configs)
        
        # Verify user namespace configuration
        user_config = self.namespace_manager._namespace_configs['/']
        self.assertEqual(user_config.name, '/')
        self.assertEqual(user_config.namespace_type, NamespaceType.USER)
        self.assertTrue(user_config.auth_required)
        self.assertFalse(user_config.admin_only)
        
        # Verify admin namespace configuration
        admin_config = self.namespace_manager._namespace_configs['/admin']
        self.assertEqual(admin_config.name, '/admin')
        self.assertEqual(admin_config.namespace_type, NamespaceType.ADMIN)
        self.assertTrue(admin_config.auth_required)
        self.assertTrue(admin_config.admin_only)
    
    def test_setup_user_namespace(self):
        """Test user namespace setup"""
        # Clear existing configuration
        self.namespace_manager._namespace_configs.clear()
        
        # Setup user namespace
        self.namespace_manager.setup_user_namespace()
        
        # Verify configuration
        self.assertIn('/', self.namespace_manager._namespace_configs)
        config = self.namespace_manager._namespace_configs['/']
        
        self.assertEqual(config.name, '/')
        self.assertEqual(config.namespace_type, NamespaceType.USER)
        self.assertTrue(config.auth_required)
        self.assertFalse(config.admin_only)
        self.assertEqual(config.max_connections_per_user, 5)
        
        # Verify allowed events
        expected_events = {
            'connect', 'disconnect', 'join_room', 'leave_room',
            'caption_progress', 'caption_status', 'platform_status',
            'notification', 'user_activity'
        }
        self.assertEqual(config.allowed_events, expected_events)
    
    def test_setup_admin_namespace(self):
        """Test admin namespace setup"""
        # Clear existing configuration
        self.namespace_manager._namespace_configs.clear()
        
        # Setup admin namespace
        self.namespace_manager.setup_admin_namespace()
        
        # Verify configuration
        self.assertIn('/admin', self.namespace_manager._namespace_configs)
        config = self.namespace_manager._namespace_configs['/admin']
        
        self.assertEqual(config.name, '/admin')
        self.assertEqual(config.namespace_type, NamespaceType.ADMIN)
        self.assertTrue(config.auth_required)
        self.assertTrue(config.admin_only)
        self.assertEqual(config.max_connections_per_user, 3)
        
        # Verify allowed events
        expected_events = {
            'connect', 'disconnect', 'join_room', 'leave_room',
            'system_status', 'user_management', 'platform_management',
            'maintenance_operations', 'security_monitoring',
            'configuration_management', 'admin_notification'
        }
        self.assertEqual(config.allowed_events, expected_events)
        
        # Verify required permissions
        expected_permissions = {
            'system_management', 'user_management', 'platform_management'
        }
        self.assertEqual(config.required_permissions, expected_permissions)
    
    def test_register_event_handlers(self):
        """Test event handler registration"""
        # Mock handlers
        mock_handler1 = Mock()
        mock_handler2 = Mock()
        
        handlers = {
            'user_activity': mock_handler1,  # Use allowed event
            'notification': mock_handler2    # Use allowed event
        }
        
        # Register handlers for user namespace
        self.namespace_manager.register_event_handlers('/', handlers)
        
        # Verify handlers are stored
        self.assertIn('user_activity', self.namespace_manager._event_handlers['/'])
        self.assertIn('notification', self.namespace_manager._event_handlers['/'])
    
    def test_register_event_handlers_invalid_namespace(self):
        """Test event handler registration with invalid namespace"""
        handlers = {'test_event': Mock()}
        
        # Should raise error for unconfigured namespace
        with self.assertRaises(RuntimeError):
            self.namespace_manager.register_event_handlers('/invalid', handlers)
    
    def test_create_room(self):
        """Test room creation"""
        # Create room
        result = self.namespace_manager.create_room(
            'test_room', '/', 'general', 1, {'description': 'Test room'}
        )
        
        self.assertTrue(result)
        
        # Verify room was created
        self.assertIn('test_room', self.namespace_manager._rooms)
        room_info = self.namespace_manager._rooms['test_room']
        
        self.assertEqual(room_info.room_id, 'test_room')
        self.assertEqual(room_info.namespace, '/')
        self.assertEqual(room_info.room_type, 'general')
        self.assertEqual(room_info.created_by, 1)
        self.assertEqual(room_info.metadata['description'], 'Test room')
        
        # Verify room is tracked by namespace
        self.assertIn('test_room', self.namespace_manager._namespace_rooms['/'])
    
    def test_create_room_duplicate(self):
        """Test creating duplicate room"""
        # Create room
        self.namespace_manager.create_room('test_room', '/', 'general', 1)
        
        # Try to create duplicate
        result = self.namespace_manager.create_room('test_room', '/', 'general', 2)
        
        self.assertFalse(result)
    
    def test_create_room_invalid_namespace(self):
        """Test creating room in invalid namespace"""
        result = self.namespace_manager.create_room(
            'test_room', '/invalid', 'general', 1
        )
        
        self.assertFalse(result)
    
    @patch('websocket_namespace_manager.join_room')
    @patch('websocket_namespace_manager.emit')
    def test_join_user_room(self, mock_emit, mock_join_room):
        """Test user joining a room"""
        # No need to mock request.sid for this test
        
        # Create connection and room
        connection_info = ConnectionInfo(
            session_id='session_123',
            namespace='/',
            user_id=1,
            username='testuser',
            role=UserRole.REVIEWER,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=self.mock_auth_context
        )
        
        self.namespace_manager._connections['session_123'] = connection_info
        self.namespace_manager.create_room('test_room', '/', 'general', 1)
        
        # Join room
        result = self.namespace_manager.join_user_room('session_123', 'test_room')
        
        self.assertTrue(result)
        
        # Verify SocketIO join_room was called
        mock_join_room.assert_called_once_with('test_room', namespace='/')
        
        # Verify tracking was updated
        room_info = self.namespace_manager._rooms['test_room']
        self.assertIn('session_123', room_info.members)
        self.assertIn('test_room', connection_info.rooms)
        self.assertIn('test_room', self.namespace_manager._user_rooms[1])
        
        # Verify room_joined event was emitted
        mock_emit.assert_called_once()
    
    def test_join_user_room_invalid_session(self):
        """Test joining room with invalid session"""
        result = self.namespace_manager.join_user_room('invalid_session', 'test_room')
        self.assertFalse(result)
    
    def test_join_user_room_invalid_room(self):
        """Test joining invalid room"""
        # Create connection
        connection_info = ConnectionInfo(
            session_id='session_123',
            namespace='/',
            user_id=1,
            username='testuser',
            role=UserRole.REVIEWER,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=self.mock_auth_context
        )
        
        self.namespace_manager._connections['session_123'] = connection_info
        
        result = self.namespace_manager.join_user_room('session_123', 'invalid_room')
        self.assertFalse(result)
    
    @patch('websocket_namespace_manager.leave_room')
    @patch('websocket_namespace_manager.emit')
    def test_leave_user_room(self, mock_emit, mock_leave_room):
        """Test user leaving a room"""
        # No need to mock request.sid for this test
        
        # Create connection and room
        connection_info = ConnectionInfo(
            session_id='session_123',
            namespace='/',
            user_id=1,
            username='testuser',
            role=UserRole.REVIEWER,
            connected_at=datetime.now(timezone.utc),
            rooms={'test_room'},
            auth_context=self.mock_auth_context
        )
        
        self.namespace_manager._connections['session_123'] = connection_info
        self.namespace_manager.create_room('test_room', '/', 'general', 1)
        
        # Add user to room tracking
        room_info = self.namespace_manager._rooms['test_room']
        room_info.members.add('session_123')
        self.namespace_manager._user_rooms[1].add('test_room')
        
        # Leave room
        result = self.namespace_manager.leave_user_room('session_123', 'test_room')
        
        self.assertTrue(result)
        
        # Verify SocketIO leave_room was called
        mock_leave_room.assert_called_once_with('test_room', namespace='/')
        
        # Verify tracking was updated
        self.assertNotIn('session_123', room_info.members)
        self.assertNotIn('test_room', connection_info.rooms)
        self.assertNotIn('test_room', self.namespace_manager._user_rooms[1])
        
        # Verify room_left event was emitted
        mock_emit.assert_called_once()
    
    @patch('websocket_namespace_manager.emit')
    def test_broadcast_to_room(self, mock_emit):
        """Test broadcasting to a room"""
        # Create room
        self.namespace_manager.create_room('test_room', '/', 'general', 1)
        room_info = self.namespace_manager._rooms['test_room']
        room_info.members.add('session_1')
        room_info.members.add('session_2')
        
        # Broadcast message
        test_data = {'message': 'Hello room'}
        result = self.namespace_manager.broadcast_to_room('test_room', 'test_event', test_data)
        
        self.assertTrue(result)
        
        # Verify emit was called with correct data
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        
        # Check event data includes broadcast metadata
        event_data = call_args[0][1]
        self.assertEqual(event_data['message'], 'Hello room')
        self.assertEqual(event_data['room_id'], 'test_room')
        self.assertEqual(event_data['member_count'], 2)
        self.assertIn('broadcast_timestamp', event_data)
    
    @patch('websocket_namespace_manager.emit')
    def test_broadcast_to_room_with_exclusion(self, mock_emit):
        """Test broadcasting to room with session exclusion"""
        # Create room
        self.namespace_manager.create_room('test_room', '/', 'general', 1)
        room_info = self.namespace_manager._rooms['test_room']
        room_info.members.add('session_1')
        room_info.members.add('session_2')
        
        # Broadcast message excluding one session
        test_data = {'message': 'Hello room'}
        result = self.namespace_manager.broadcast_to_room(
            'test_room', 'test_event', test_data, exclude_session='session_1'
        )
        
        self.assertTrue(result)
        
        # Verify emit was called for each non-excluded session
        self.assertEqual(mock_emit.call_count, 1)  # Only session_2 should receive
    
    @patch('websocket_namespace_manager.emit')
    def test_broadcast_to_namespace(self, mock_emit):
        """Test broadcasting to entire namespace"""
        # Add connections to namespace
        self.namespace_manager._namespace_connections['/'].add('session_1')
        self.namespace_manager._namespace_connections['/'].add('session_2')
        
        # Broadcast message
        test_data = {'message': 'Hello namespace'}
        result = self.namespace_manager.broadcast_to_namespace('/', 'test_event', test_data)
        
        self.assertTrue(result)
        
        # Verify emit was called
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        
        # Check event data includes broadcast metadata
        event_data = call_args[0][1]
        self.assertEqual(event_data['message'], 'Hello namespace')
        self.assertEqual(event_data['namespace'], '/')
        self.assertIn('broadcast_timestamp', event_data)
    
    @patch('websocket_namespace_manager.emit')
    def test_broadcast_to_namespace_with_role_filter(self, mock_emit):
        """Test broadcasting to namespace with role filter"""
        # Create connections with different roles
        admin_connection = ConnectionInfo(
            session_id='admin_session',
            namespace='/',
            user_id=1,
            username='admin',
            role=UserRole.ADMIN,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=self.mock_admin_context
        )
        
        user_connection = ConnectionInfo(
            session_id='user_session',
            namespace='/',
            user_id=2,
            username='user',
            role=UserRole.REVIEWER,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=self.mock_auth_context
        )
        
        self.namespace_manager._connections['admin_session'] = admin_connection
        self.namespace_manager._connections['user_session'] = user_connection
        self.namespace_manager._namespace_connections['/'].add('admin_session')
        self.namespace_manager._namespace_connections['/'].add('user_session')
        
        # Broadcast to admin role only
        test_data = {'message': 'Admin only message'}
        result = self.namespace_manager.broadcast_to_namespace(
            '/', 'admin_event', test_data, role_filter=UserRole.ADMIN
        )
        
        self.assertTrue(result)
        
        # Verify emit was called only for admin session
        mock_emit.assert_called_once()
    
    def test_get_namespace_stats(self):
        """Test getting namespace statistics"""
        # Add some test data
        connection_info = ConnectionInfo(
            session_id='session_123',
            namespace='/',
            user_id=1,
            username='testuser',
            role=UserRole.REVIEWER,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=self.mock_auth_context
        )
        
        self.namespace_manager._connections['session_123'] = connection_info
        self.namespace_manager._namespace_connections['/'].add('session_123')
        self.namespace_manager.create_room('test_room', '/', 'general', 1)
        
        # Get stats
        stats = self.namespace_manager.get_namespace_stats('/')
        
        # Verify stats
        self.assertEqual(stats['namespace'], '/')
        self.assertEqual(stats['namespace_type'], 'user')
        self.assertTrue(stats['auth_required'])
        self.assertFalse(stats['admin_only'])
        self.assertEqual(stats['total_connections'], 1)
        self.assertEqual(stats['unique_users'], 1)
        self.assertEqual(stats['connections_by_role']['reviewer'], 1)
        self.assertEqual(stats['room_statistics']['total_rooms'], 3)  # Including default rooms
    
    def test_get_namespace_stats_invalid_namespace(self):
        """Test getting stats for invalid namespace"""
        stats = self.namespace_manager.get_namespace_stats('/invalid')
        self.assertIn('error', stats)
    
    def test_handle_namespace_connect_success(self):
        """Test successful namespace connection"""
        # Create a mock Flask app context to avoid request context issues
        from flask import Flask
        app = Flask(__name__)
        
        with app.test_request_context():
            with patch('websocket_namespace_manager.request') as mock_request:
                with patch('websocket_namespace_manager.emit'):
                    # Setup mocks
                    mock_request.sid = 'session_123'
                    
                    self.mock_auth_handler.authenticate_connection.return_value = (
                        AuthenticationResult.SUCCESS, self.mock_auth_context
                    )
                    
                    # Handle connection
                    result = self.namespace_manager._handle_namespace_connect('/', None)
                    
                    self.assertTrue(result)
                    
                    # Verify connection was stored
                    self.assertIn('session_123', self.namespace_manager._connections)
                    connection = self.namespace_manager._connections['session_123']
                    self.assertEqual(connection.user_id, 1)
                    self.assertEqual(connection.username, 'testuser')
                    self.assertEqual(connection.namespace, '/')
                    
                    # Verify tracking was updated
                    self.assertIn('session_123', self.namespace_manager._user_connections[1])
                    self.assertIn('session_123', self.namespace_manager._namespace_connections['/'])
    
    def test_handle_namespace_connect_auth_failure(self):
        """Test namespace connection with authentication failure"""
        # Create a mock Flask app context to avoid request context issues
        from flask import Flask
        app = Flask(__name__)
        
        with app.test_request_context():
            with patch('websocket_namespace_manager.request') as mock_request:
                # Setup mocks
                mock_request.sid = 'session_123'
                
                self.mock_auth_handler.authenticate_connection.return_value = (
                    AuthenticationResult.INVALID_SESSION, None
                )
                
                # Handle connection
                result = self.namespace_manager._handle_namespace_connect('/', None)
                
                self.assertFalse(result)
                
                # Verify connection was not stored
                self.assertNotIn('session_123', self.namespace_manager._connections)
                
                # Verify auth failure handler was called
                self.mock_auth_handler.handle_authentication_failure.assert_called_once()
    
    def test_handle_namespace_connect_admin_namespace_non_admin(self):
        """Test non-admin user connecting to admin namespace"""
        # Create a mock Flask app context to avoid request context issues
        from flask import Flask
        app = Flask(__name__)
        
        with app.test_request_context():
            with patch('websocket_namespace_manager.request') as mock_request:
                # Setup mocks
                mock_request.sid = 'session_123'
                
                self.mock_auth_handler.authenticate_connection.return_value = (
                    AuthenticationResult.SUCCESS, self.mock_auth_context  # Non-admin user
                )
                
                # Handle connection to admin namespace
                result = self.namespace_manager._handle_namespace_connect('/admin', None)
                
                self.assertFalse(result)
                
                # Verify connection was not stored
                self.assertNotIn('session_123', self.namespace_manager._connections)
    
    def test_handle_namespace_connect_admin_namespace_admin_user(self):
        """Test admin user connecting to admin namespace"""
        # Create a mock Flask app context to avoid request context issues
        from flask import Flask
        app = Flask(__name__)
        
        with app.test_request_context():
            with patch('websocket_namespace_manager.request') as mock_request:
                with patch('websocket_namespace_manager.emit'):
                    # Setup mocks
                    mock_request.sid = 'admin_session'
                    
                    # Add required permissions to admin context
                    self.mock_admin_context.permissions = [
                        'system_management', 'user_management', 'platform_management'
                    ]
                    
                    self.mock_auth_handler.authenticate_connection.return_value = (
                        AuthenticationResult.SUCCESS, self.mock_admin_context  # Admin user
                    )
                    
                    # Handle connection to admin namespace
                    result = self.namespace_manager._handle_namespace_connect('/admin', None)
                    
                    self.assertTrue(result)
                    
                    # Verify connection was stored
                    self.assertIn('admin_session', self.namespace_manager._connections)
                    connection = self.namespace_manager._connections['admin_session']
                    self.assertEqual(connection.user_id, 2)
                    self.assertEqual(connection.username, 'admin')
                    self.assertEqual(connection.namespace, '/admin')
    
    def test_handle_namespace_disconnect(self):
        """Test namespace disconnection"""
        # Create a mock Flask app context to avoid request context issues
        from flask import Flask
        app = Flask(__name__)
        
        with app.test_request_context():
            with patch('websocket_namespace_manager.request') as mock_request:
                with patch('websocket_namespace_manager.leave_room'):
                    # Setup mocks
                    mock_request.sid = 'session_123'
                    
                    # Create connection
                    connection_info = ConnectionInfo(
                        session_id='session_123',
                        namespace='/',
                        user_id=1,
                        username='testuser',
                        role=UserRole.REVIEWER,
                        connected_at=datetime.now(timezone.utc),
                        rooms={'test_room'},
                        auth_context=self.mock_auth_context
                    )
                    
                    self.namespace_manager._connections['session_123'] = connection_info
                    self.namespace_manager._user_connections[1].add('session_123')
                    self.namespace_manager._namespace_connections['/'].add('session_123')
                    
                    # Create room and add user
                    self.namespace_manager.create_room('test_room', '/', 'general', 1)
                    room_info = self.namespace_manager._rooms['test_room']
                    room_info.members.add('session_123')
                    
                    # Handle disconnection
                    self.namespace_manager._handle_namespace_disconnect('/')
                    
                    # Verify connection was removed
                    self.assertNotIn('session_123', self.namespace_manager._connections)
                    self.assertNotIn('session_123', self.namespace_manager._user_connections[1])
                    self.assertNotIn('session_123', self.namespace_manager._namespace_connections['/'])
    
    def test_validate_namespace_access_user_namespace(self):
        """Test namespace access validation for user namespace"""
        # Regular user should have access to user namespace
        result = self.namespace_manager._validate_namespace_access(self.mock_auth_context, '/')
        self.assertTrue(result)
        
        # Admin user should also have access to user namespace
        result = self.namespace_manager._validate_namespace_access(self.mock_admin_context, '/')
        self.assertTrue(result)
    
    def test_validate_namespace_access_admin_namespace(self):
        """Test namespace access validation for admin namespace"""
        # Regular user should not have access to admin namespace
        result = self.namespace_manager._validate_namespace_access(self.mock_auth_context, '/admin')
        self.assertFalse(result)
        
        # Admin user should have access to admin namespace
        # Add required permissions to admin context
        self.mock_admin_context.permissions = [
            'system_management', 'user_management', 'platform_management'
        ]
        result = self.namespace_manager._validate_namespace_access(self.mock_admin_context, '/admin')
        self.assertTrue(result)
    
    def test_check_connection_limits(self):
        """Test connection limit checking"""
        # Add connections for user
        for i in range(3):
            session_id = f'session_{i}'
            self.namespace_manager._user_connections[1].add(session_id)
            self.namespace_manager._namespace_connections['/'].add(session_id)
        
        # Should still be under limit (5 max for user namespace)
        result = self.namespace_manager._check_connection_limits(1, '/')
        self.assertTrue(result)
        
        # Add more connections to exceed limit
        for i in range(3, 6):
            session_id = f'session_{i}'
            self.namespace_manager._user_connections[1].add(session_id)
            self.namespace_manager._namespace_connections['/'].add(session_id)
        
        # Should now be at limit
        result = self.namespace_manager._check_connection_limits(1, '/')
        self.assertFalse(result)
    
    def test_validate_room_access_general_room(self):
        """Test room access validation for general room"""
        # Create general room
        room_info = RoomInfo(
            room_id='general_room',
            namespace='/',
            room_type='general',
            created_at=datetime.now(timezone.utc),
            created_by=1,
            members=set(),
            metadata={}
        )
        
        connection_info = ConnectionInfo(
            session_id='session_123',
            namespace='/',
            user_id=1,
            username='testuser',
            role=UserRole.REVIEWER,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=self.mock_auth_context
        )
        
        # Regular user should have access to general room
        result = self.namespace_manager._validate_room_access(connection_info, room_info)
        self.assertTrue(result)
    
    def test_validate_room_access_admin_room(self):
        """Test room access validation for admin room"""
        # Create admin room
        room_info = RoomInfo(
            room_id='admin_room',
            namespace='/admin',
            room_type='admin',
            created_at=datetime.now(timezone.utc),
            created_by=2,
            members=set(),
            metadata={}
        )
        
        connection_info = ConnectionInfo(
            session_id='session_123',
            namespace='/',
            user_id=1,
            username='testuser',
            role=UserRole.REVIEWER,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=self.mock_auth_context
        )
        
        admin_connection_info = ConnectionInfo(
            session_id='admin_session',
            namespace='/admin',
            user_id=2,
            username='admin',
            role=UserRole.ADMIN,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=self.mock_admin_context
        )
        
        # Regular user should not have access to admin room
        result = self.namespace_manager._validate_room_access(connection_info, room_info)
        self.assertFalse(result)
        
        # Admin user should have access to admin room
        result = self.namespace_manager._validate_room_access(admin_connection_info, room_info)
        self.assertTrue(result)
    
    def test_cleanup_inactive_connections(self):
        """Test cleanup of inactive connections"""
        # Create old connection (simulate 2 hours ago)
        old_time = datetime.now(timezone.utc).replace(hour=datetime.now(timezone.utc).hour - 2)
        
        connection_info = ConnectionInfo(
            session_id='old_session',
            namespace='/',
            user_id=1,
            username='testuser',
            role=UserRole.REVIEWER,
            connected_at=old_time,
            rooms=set(),
            auth_context=self.mock_auth_context
        )
        
        self.namespace_manager._connections['old_session'] = connection_info
        self.namespace_manager._user_connections[1].add('old_session')
        self.namespace_manager._namespace_connections['/'].add('old_session')
        
        # Mock session validation to return False (inactive)
        self.mock_auth_handler.validate_user_session.return_value = False
        
        # Run cleanup
        self.namespace_manager.cleanup_inactive_connections()
        
        # Verify connection was removed
        self.assertNotIn('old_session', self.namespace_manager._connections)
        self.assertNotIn('old_session', self.namespace_manager._user_connections[1])
        self.assertNotIn('old_session', self.namespace_manager._namespace_connections['/'])
    
    def test_get_manager_status(self):
        """Test getting manager status"""
        # Add some test data
        connection_info = ConnectionInfo(
            session_id='session_123',
            namespace='/',
            user_id=1,
            username='testuser',
            role=UserRole.REVIEWER,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=self.mock_auth_context
        )
        
        self.namespace_manager._connections['session_123'] = connection_info
        self.namespace_manager._user_connections[1].add('session_123')
        self.namespace_manager._namespace_connections['/'].add('session_123')
        self.namespace_manager.create_room('test_room', '/', 'general', 1)
        
        # Get status
        status = self.namespace_manager.get_manager_status()
        
        # Verify status
        self.assertIn('configured_namespaces', status)
        self.assertIn('/', status['configured_namespaces'])
        self.assertIn('/admin', status['configured_namespaces'])
        
        self.assertEqual(status['total_connections'], 1)
        self.assertEqual(status['unique_users'], 1)
        self.assertEqual(status['connections_by_namespace']['/'], 1)
        self.assertGreaterEqual(status['total_rooms'], 1)


class TestNamespaceConfig(unittest.TestCase):
    """Test cases for NamespaceConfig dataclass"""
    
    def test_namespace_config_creation(self):
        """Test namespace configuration creation"""
        config = NamespaceConfig(
            name='/test',
            namespace_type=NamespaceType.USER,
            auth_required=True,
            admin_only=False
        )
        
        self.assertEqual(config.name, '/test')
        self.assertEqual(config.namespace_type, NamespaceType.USER)
        self.assertTrue(config.auth_required)
        self.assertFalse(config.admin_only)
        self.assertEqual(config.max_connections_per_user, 5)
        self.assertIsInstance(config.allowed_events, set)
        self.assertIsInstance(config.required_permissions, set)
    
    def test_namespace_config_with_events_and_permissions(self):
        """Test namespace configuration with events and permissions"""
        allowed_events = {'connect', 'disconnect', 'test_event'}
        required_permissions = {'test_permission'}
        
        config = NamespaceConfig(
            name='/test',
            namespace_type=NamespaceType.ADMIN,
            allowed_events=allowed_events,
            required_permissions=required_permissions
        )
        
        self.assertEqual(config.allowed_events, allowed_events)
        self.assertEqual(config.required_permissions, required_permissions)


class TestRoomInfo(unittest.TestCase):
    """Test cases for RoomInfo dataclass"""
    
    def test_room_info_creation(self):
        """Test room info creation"""
        room_info = RoomInfo(
            room_id='test_room',
            namespace='/',
            room_type='general',
            created_at=datetime.now(timezone.utc),
            created_by=1,
            members=set(),
            metadata={'description': 'Test room'}
        )
        
        self.assertEqual(room_info.room_id, 'test_room')
        self.assertEqual(room_info.namespace, '/')
        self.assertEqual(room_info.room_type, 'general')
        self.assertEqual(room_info.created_by, 1)
        self.assertIsInstance(room_info.members, set)
        self.assertEqual(room_info.metadata['description'], 'Test room')


class TestConnectionInfo(unittest.TestCase):
    """Test cases for ConnectionInfo dataclass"""
    
    def test_connection_info_creation(self):
        """Test connection info creation"""
        auth_context = AuthenticationContext(
            user_id=1,
            username='testuser',
            email='test@example.com',
            role=UserRole.REVIEWER,
            session_id='test_session'
        )
        
        connection_info = ConnectionInfo(
            session_id='session_123',
            namespace='/',
            user_id=1,
            username='testuser',
            role=UserRole.REVIEWER,
            connected_at=datetime.now(timezone.utc),
            rooms=set(),
            auth_context=auth_context
        )
        
        self.assertEqual(connection_info.session_id, 'session_123')
        self.assertEqual(connection_info.namespace, '/')
        self.assertEqual(connection_info.user_id, 1)
        self.assertEqual(connection_info.username, 'testuser')
        self.assertEqual(connection_info.role, UserRole.REVIEWER)
        self.assertIsInstance(connection_info.rooms, set)
        self.assertEqual(connection_info.auth_context, auth_context)


if __name__ == '__main__':
    unittest.main()
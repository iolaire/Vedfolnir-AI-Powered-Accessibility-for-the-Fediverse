# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Namespace Manager

This module provides comprehensive namespace management for organizing user and admin
functionality with separate namespaces, shared authentication, room management for
targeted message broadcasting, event handler registration system, and namespace-specific
security validation.
"""

import logging
from typing import Dict, Any, Optional, Callable, List, Set, Tuple
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms, disconnect

from websocket_auth_handler import WebSocketAuthHandler, AuthenticationResult, AuthenticationContext
from models import UserRole

logger = logging.getLogger(__name__)


class NamespaceType(Enum):
    """WebSocket namespace types"""
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class NamespaceConfig:
    """Configuration for a WebSocket namespace"""
    name: str
    namespace_type: NamespaceType
    auth_required: bool = True
    admin_only: bool = False
    rate_limit_enabled: bool = True
    max_connections_per_user: int = 5
    allowed_events: Set[str] = None
    required_permissions: Set[str] = None
    
    def __post_init__(self):
        if self.allowed_events is None:
            self.allowed_events = set()
        if self.required_permissions is None:
            self.required_permissions = set()


@dataclass
class RoomInfo:
    """Information about a WebSocket room"""
    room_id: str
    namespace: str
    room_type: str
    created_at: datetime
    created_by: int
    members: Set[str]
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.members is None:
            self.members = set()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection"""
    session_id: str
    namespace: str
    user_id: int
    username: str
    role: UserRole
    connected_at: datetime
    rooms: Set[str]
    auth_context: AuthenticationContext
    
    def __post_init__(self):
        if self.rooms is None:
            self.rooms = set()


class WebSocketNamespaceManager:
    """
    Comprehensive namespace manager for organizing user and admin functionality
    
    Provides separate namespaces with shared authentication, room management for
    targeted message broadcasting, event handler registration system, and
    namespace-specific security validation.
    """
    
    def __init__(self, socketio: SocketIO, auth_handler: WebSocketAuthHandler):
        """
        Initialize namespace manager
        
        Args:
            socketio: SocketIO instance
            auth_handler: WebSocket authentication handler
        """
        self.socketio = socketio
        self.auth_handler = auth_handler
        self.logger = logging.getLogger(__name__)
        
        # Namespace configurations
        self._namespace_configs = {}
        
        # Connection tracking
        self._connections = {}  # session_id -> ConnectionInfo
        self._user_connections = defaultdict(set)  # user_id -> set of session_ids
        self._namespace_connections = defaultdict(set)  # namespace -> set of session_ids
        
        # Room management
        self._rooms = {}  # room_id -> RoomInfo
        self._user_rooms = defaultdict(set)  # user_id -> set of room_ids
        self._namespace_rooms = defaultdict(set)  # namespace -> set of room_ids
        
        # Event handlers
        self._event_handlers = defaultdict(dict)  # namespace -> {event_name: handler}
        self._middleware_handlers = defaultdict(list)  # namespace -> [middleware_functions]
        
        # Security tracking
        self._security_violations = []
        self._rate_limit_violations = defaultdict(list)  # user_id -> [timestamps]
        
        # Initialize default namespaces
        self._setup_default_namespaces()
    
    def setup_user_namespace(self) -> None:
        """
        Setup user namespace for regular user functionality
        """
        try:
            namespace_config = NamespaceConfig(
                name='/',
                namespace_type=NamespaceType.USER,
                auth_required=True,
                admin_only=False,
                rate_limit_enabled=True,
                max_connections_per_user=5,
                allowed_events={
                    'connect', 'disconnect', 'join_room', 'leave_room',
                    'caption_progress', 'caption_status', 'platform_status',
                    'notification', 'user_activity'
                },
                required_permissions=set()
            )
            
            self._register_namespace_config('/', namespace_config)
            
            # Setup user namespace handlers
            self._setup_user_connection_handlers()
            self._setup_user_event_handlers()
            self._setup_user_room_handlers()
            
            self.logger.info("User namespace configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup user namespace: {e}")
            raise RuntimeError(f"User namespace setup failed: {e}")
    
    def setup_admin_namespace(self) -> None:
        """
        Setup admin namespace for administrative functionality
        """
        try:
            namespace_config = NamespaceConfig(
                name='/admin',
                namespace_type=NamespaceType.ADMIN,
                auth_required=True,
                admin_only=True,
                rate_limit_enabled=True,
                max_connections_per_user=3,
                allowed_events={
                    'connect', 'disconnect', 'join_room', 'leave_room',
                    'system_status', 'user_management', 'platform_management',
                    'maintenance_operations', 'security_monitoring',
                    'configuration_management', 'admin_notification'
                },
                required_permissions={
                    'system_management', 'user_management', 'platform_management'
                }
            )
            
            self._register_namespace_config('/admin', namespace_config)
            
            # Setup admin namespace handlers
            self._setup_admin_connection_handlers()
            self._setup_admin_event_handlers()
            self._setup_admin_room_handlers()
            
            self.logger.info("Admin namespace configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup admin namespace: {e}")
            raise RuntimeError(f"Admin namespace setup failed: {e}")
    
    def register_event_handlers(self, namespace: str, handlers: Dict[str, Callable]) -> None:
        """
        Register event handlers for a namespace
        
        Args:
            namespace: Namespace to register handlers for
            handlers: Dictionary mapping event names to handler functions
        """
        try:
            if namespace not in self._namespace_configs:
                raise ValueError(f"Namespace {namespace} not configured")
            
            namespace_config = self._namespace_configs[namespace]
            
            for event_name, handler in handlers.items():
                # Validate event is allowed for namespace
                if (namespace_config.allowed_events and 
                    event_name not in namespace_config.allowed_events and
                    event_name not in {'connect', 'disconnect'}):
                    self.logger.warning(f"Event {event_name} not allowed for namespace {namespace}")
                    continue
                
                # Wrap handler with security validation
                wrapped_handler = self._wrap_event_handler(namespace, event_name, handler)
                
                # Register with SocketIO
                self.socketio.on(event_name, namespace=namespace)(wrapped_handler)
                
                # Store handler reference
                self._event_handlers[namespace][event_name] = handler
                
                self.logger.debug(f"Registered event handler: {event_name} for namespace {namespace}")
            
            self.logger.info(f"Registered {len(handlers)} event handlers for namespace {namespace}")
            
        except Exception as e:
            self.logger.error(f"Failed to register event handlers for namespace {namespace}: {e}")
            raise RuntimeError(f"Event handler registration failed: {e}")
    
    def create_room(self, room_id: str, namespace: str, room_type: str, 
                   created_by: int, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a room for targeted message broadcasting
        
        Args:
            room_id: Unique room identifier
            namespace: Namespace the room belongs to
            room_type: Type of room (e.g., 'user', 'admin', 'broadcast')
            created_by: User ID who created the room
            metadata: Optional room metadata
            
        Returns:
            True if room created successfully, False otherwise
        """
        try:
            if room_id in self._rooms:
                self.logger.warning(f"Room {room_id} already exists")
                return False
            
            if namespace not in self._namespace_configs:
                self.logger.error(f"Cannot create room in unconfigured namespace: {namespace}")
                return False
            
            room_info = RoomInfo(
                room_id=room_id,
                namespace=namespace,
                room_type=room_type,
                created_at=datetime.now(timezone.utc),
                created_by=created_by,
                members=set(),
                metadata=metadata or {}
            )
            
            self._rooms[room_id] = room_info
            self._namespace_rooms[namespace].add(room_id)
            
            self.logger.info(f"Created room {room_id} in namespace {namespace} by user {created_by}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create room {room_id}: {e}")
            return False
    
    def join_user_room(self, session_id: str, room_id: str) -> bool:
        """
        Add user to a room
        
        Args:
            session_id: User's session ID
            room_id: Room to join
            
        Returns:
            True if joined successfully, False otherwise
        """
        try:
            if session_id not in self._connections:
                self.logger.error(f"Session {session_id} not found")
                return False
            
            if room_id not in self._rooms:
                self.logger.error(f"Room {room_id} not found")
                return False
            
            connection = self._connections[session_id]
            room_info = self._rooms[room_id]
            
            # Validate namespace match
            if connection.namespace != room_info.namespace:
                self.logger.error(f"Namespace mismatch: connection in {connection.namespace}, room in {room_info.namespace}")
                return False
            
            # Validate permissions for room type
            if not self._validate_room_access(connection, room_info):
                self.logger.warning(f"User {connection.user_id} denied access to room {room_id}")
                return False
            
            # Join room in SocketIO
            join_room(room_id, namespace=connection.namespace)
            
            # Update tracking
            room_info.members.add(session_id)
            connection.rooms.add(room_id)
            self._user_rooms[connection.user_id].add(room_id)
            
            self.logger.info(f"User {connection.username} joined room {room_id}")
            
            # Emit room joined event
            emit('room_joined', {
                'room_id': room_id,
                'room_type': room_info.room_type,
                'member_count': len(room_info.members),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, namespace=connection.namespace)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to join room {room_id}: {e}")
            return False
    
    def leave_user_room(self, session_id: str, room_id: str) -> bool:
        """
        Remove user from a room
        
        Args:
            session_id: User's session ID
            room_id: Room to leave
            
        Returns:
            True if left successfully, False otherwise
        """
        try:
            if session_id not in self._connections:
                self.logger.error(f"Session {session_id} not found")
                return False
            
            if room_id not in self._rooms:
                self.logger.error(f"Room {room_id} not found")
                return False
            
            connection = self._connections[session_id]
            room_info = self._rooms[room_id]
            
            # Leave room in SocketIO
            leave_room(room_id, namespace=connection.namespace)
            
            # Update tracking
            room_info.members.discard(session_id)
            connection.rooms.discard(room_id)
            self._user_rooms[connection.user_id].discard(room_id)
            
            self.logger.info(f"User {connection.username} left room {room_id}")
            
            # Emit room left event
            emit('room_left', {
                'room_id': room_id,
                'room_type': room_info.room_type,
                'member_count': len(room_info.members),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, namespace=connection.namespace)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to leave room {room_id}: {e}")
            return False
    
    def broadcast_to_room(self, room_id: str, event: str, data: Dict[str, Any], 
                         exclude_session: Optional[str] = None) -> bool:
        """
        Broadcast message to all users in a room
        
        Args:
            room_id: Room to broadcast to
            event: Event name
            data: Event data
            exclude_session: Optional session ID to exclude from broadcast
            
        Returns:
            True if broadcast successful, False otherwise
        """
        try:
            if room_id not in self._rooms:
                self.logger.error(f"Room {room_id} not found")
                return False
            
            room_info = self._rooms[room_id]
            
            # Add broadcast metadata
            broadcast_data = {
                **data,
                'room_id': room_id,
                'broadcast_timestamp': datetime.now(timezone.utc).isoformat(),
                'member_count': len(room_info.members)
            }
            
            # Broadcast to room
            if exclude_session:
                # Emit to room excluding specific session
                for session_id in room_info.members:
                    if session_id != exclude_session:
                        emit(event, broadcast_data, 
                             room=session_id, namespace=room_info.namespace)
            else:
                # Emit to entire room
                emit(event, broadcast_data, 
                     room=room_id, namespace=room_info.namespace)
            
            self.logger.debug(f"Broadcasted {event} to room {room_id} ({len(room_info.members)} members)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast to room {room_id}: {e}")
            return False
    
    def broadcast_to_namespace(self, namespace: str, event: str, data: Dict[str, Any],
                              role_filter: Optional[UserRole] = None) -> bool:
        """
        Broadcast message to all users in a namespace
        
        Args:
            namespace: Namespace to broadcast to
            event: Event name
            data: Event data
            role_filter: Optional role filter to limit broadcast
            
        Returns:
            True if broadcast successful, False otherwise
        """
        try:
            if namespace not in self._namespace_configs:
                self.logger.error(f"Namespace {namespace} not configured")
                return False
            
            # Add broadcast metadata
            broadcast_data = {
                **data,
                'namespace': namespace,
                'broadcast_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            if role_filter:
                # Broadcast to users with specific role
                target_sessions = []
                for session_id in self._namespace_connections[namespace]:
                    connection = self._connections.get(session_id)
                    if connection and connection.role == role_filter:
                        target_sessions.append(session_id)
                
                for session_id in target_sessions:
                    emit(event, broadcast_data, room=session_id, namespace=namespace)
                
                self.logger.debug(f"Broadcasted {event} to {len(target_sessions)} users with role {role_filter.value} in namespace {namespace}")
            else:
                # Broadcast to entire namespace
                emit(event, broadcast_data, namespace=namespace)
                
                connection_count = len(self._namespace_connections[namespace])
                self.logger.debug(f"Broadcasted {event} to namespace {namespace} ({connection_count} connections)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast to namespace {namespace}: {e}")
            return False
    
    def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        """
        Get statistics for a namespace
        
        Args:
            namespace: Namespace to get stats for
            
        Returns:
            Dictionary containing namespace statistics
        """
        try:
            if namespace not in self._namespace_configs:
                return {'error': f'Namespace {namespace} not configured'}
            
            config = self._namespace_configs[namespace]
            connections = self._namespace_connections[namespace]
            rooms = self._namespace_rooms[namespace]
            
            # Count connections by role
            role_counts = defaultdict(int)
            active_users = set()
            
            for session_id in connections:
                connection = self._connections.get(session_id)
                if connection:
                    role_counts[connection.role.value] += 1
                    active_users.add(connection.user_id)
            
            # Count room statistics
            room_stats = {
                'total_rooms': len(rooms),
                'rooms_by_type': defaultdict(int)
            }
            
            for room_id in rooms:
                room_info = self._rooms.get(room_id)
                if room_info:
                    room_stats['rooms_by_type'][room_info.room_type] += 1
            
            return {
                'namespace': namespace,
                'namespace_type': config.namespace_type.value,
                'auth_required': config.auth_required,
                'admin_only': config.admin_only,
                'total_connections': len(connections),
                'unique_users': len(active_users),
                'connections_by_role': dict(role_counts),
                'room_statistics': room_stats,
                'allowed_events': list(config.allowed_events),
                'required_permissions': list(config.required_permissions),
                'max_connections_per_user': config.max_connections_per_user
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get namespace stats for {namespace}: {e}")
            return {'error': str(e)}
    
    def _setup_default_namespaces(self) -> None:
        """
        Setup default namespaces for the application
        """
        try:
            # Setup user namespace
            self.setup_user_namespace()
            
            # Setup admin namespace
            self.setup_admin_namespace()
            
            self.logger.info("Default namespaces configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup default namespaces: {e}")
            raise RuntimeError(f"Default namespace setup failed: {e}")
    
    def _register_namespace_config(self, namespace: str, config: NamespaceConfig) -> None:
        """
        Register namespace configuration
        
        Args:
            namespace: Namespace name
            config: Namespace configuration
        """
        self._namespace_configs[namespace] = config
        self.logger.debug(f"Registered configuration for namespace: {namespace}")
    
    def _setup_user_connection_handlers(self) -> None:
        """
        Setup connection handlers for user namespace
        """
        @self.socketio.on('connect', namespace='/')
        def handle_user_connect(auth=None):
            """Handle user namespace connection"""
            return self._handle_namespace_connect('/', auth)
        
        @self.socketio.on('disconnect', namespace='/')
        def handle_user_disconnect(sid=None):
            """Handle user namespace disconnection"""
            return self._handle_namespace_disconnect('/')
    
    def _setup_admin_connection_handlers(self) -> None:
        """
        Setup connection handlers for admin namespace
        """
        @self.socketio.on('connect', namespace='/admin')
        def handle_admin_connect(auth=None):
            """Handle admin namespace connection"""
            return self._handle_namespace_connect('/admin', auth)
        
        @self.socketio.on('disconnect', namespace='/admin')
        def handle_admin_disconnect(sid=None):
            """Handle admin namespace disconnection"""
            return self._handle_namespace_disconnect('/admin')
    
    def _setup_user_event_handlers(self) -> None:
        """
        Setup event handlers for user namespace
        """
        @self.socketio.on('join_room', namespace='/')
        def handle_user_join_room(data):
            """Handle user joining a room"""
            return self._handle_join_room_request('/', data)
        
        @self.socketio.on('leave_room', namespace='/')
        def handle_user_leave_room(data):
            """Handle user leaving a room"""
            return self._handle_leave_room_request('/', data)
        
        @self.socketio.on('user_activity', namespace='/')
        def handle_user_activity(data):
            """Handle user activity events"""
            return self._handle_user_activity('/', data)
    
    def _setup_admin_event_handlers(self) -> None:
        """
        Setup event handlers for admin namespace
        """
        @self.socketio.on('join_room', namespace='/admin')
        def handle_admin_join_room(data):
            """Handle admin joining a room"""
            return self._handle_join_room_request('/admin', data)
        
        @self.socketio.on('leave_room', namespace='/admin')
        def handle_admin_leave_room(data):
            """Handle admin leaving a room"""
            return self._handle_leave_room_request('/admin', data)
        
        @self.socketio.on('admin_notification', namespace='/admin')
        def handle_admin_notification(data):
            """Handle admin notification events"""
            return self._handle_admin_notification('/admin', data)
    
    def _setup_user_room_handlers(self) -> None:
        """
        Setup room management for user namespace
        """
        # Create default user rooms
        self.create_room('user_general', '/', 'general', 0, {
            'description': 'General user communication',
            'auto_join': True
        })
        
        self.create_room('caption_progress', '/', 'progress', 0, {
            'description': 'Caption generation progress updates',
            'auto_join': True
        })
    
    def _setup_admin_room_handlers(self) -> None:
        """
        Setup room management for admin namespace
        """
        # Create default admin rooms
        self.create_room('admin_general', '/admin', 'general', 0, {
            'description': 'General admin communication',
            'auto_join': True
        })
        
        self.create_room('system_monitoring', '/admin', 'monitoring', 0, {
            'description': 'System monitoring and alerts',
            'auto_join': True
        })
        
        self.create_room('security_alerts', '/admin', 'security', 0, {
            'description': 'Security alerts and notifications',
            'auto_join': True
        })
    
    def _handle_namespace_connect(self, namespace: str, auth: Optional[Dict[str, Any]]) -> bool:
        """
        Handle connection to a namespace with authentication
        
        Args:
            namespace: Namespace being connected to
            auth: Optional authentication data
            
        Returns:
            True if connection allowed, False otherwise
        """
        try:
            # Authenticate connection
            auth_result, auth_context = self.auth_handler.authenticate_connection(auth, namespace)
            
            if auth_result != AuthenticationResult.SUCCESS:
                self.logger.warning(f"Authentication failed for namespace {namespace}: {auth_result.value}")
                self.auth_handler.handle_authentication_failure(auth_result, namespace, True)
                return False
            
            # Validate namespace-specific requirements
            if not self._validate_namespace_access(auth_context, namespace):
                self.logger.warning(f"Namespace access denied for user {auth_context.username} to {namespace}")
                return False
            
            # Check connection limits
            if not self._check_connection_limits(auth_context.user_id, namespace):
                self.logger.warning(f"Connection limit exceeded for user {auth_context.user_id} in namespace {namespace}")
                return False
            
            # Create connection info
            session_id = request.sid
            connection_info = ConnectionInfo(
                session_id=session_id,
                namespace=namespace,
                user_id=auth_context.user_id,
                username=auth_context.username,
                role=auth_context.role,
                connected_at=datetime.now(timezone.utc),
                rooms=set(),
                auth_context=auth_context
            )
            
            # Store connection
            self._connections[session_id] = connection_info
            self._user_connections[auth_context.user_id].add(session_id)
            self._namespace_connections[namespace].add(session_id)
            
            # Auto-join default rooms
            self._auto_join_default_rooms(session_id, namespace)
            
            self.logger.info(f"User {auth_context.username} connected to namespace {namespace}")
            
            # Emit connection success
            emit('connection_established', {
                'namespace': namespace,
                'user_id': auth_context.user_id,
                'username': auth_context.username,
                'role': auth_context.role.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'session_id': session_id
            }, namespace=namespace)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling namespace connection: {e}")
            return False
    
    def _handle_namespace_disconnect(self, namespace: str) -> None:
        """
        Handle disconnection from a namespace
        
        Args:
            namespace: Namespace being disconnected from
        """
        try:
            session_id = request.sid
            
            if session_id not in self._connections:
                self.logger.warning(f"Disconnect from unknown session: {session_id}")
                return
            
            connection = self._connections[session_id]
            
            # Leave all rooms
            for room_id in list(connection.rooms):
                self.leave_user_room(session_id, room_id)
            
            # Remove from tracking
            self._user_connections[connection.user_id].discard(session_id)
            self._namespace_connections[namespace].discard(session_id)
            del self._connections[session_id]
            
            self.logger.info(f"User {connection.username} disconnected from namespace {namespace}")
            
        except Exception as e:
            self.logger.error(f"Error handling namespace disconnect: {e}")
    
    def _handle_join_room_request(self, namespace: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle room join request
        
        Args:
            namespace: Namespace of the request
            data: Request data containing room_id
            
        Returns:
            Response data
        """
        try:
            session_id = request.sid
            room_id = data.get('room_id')
            
            if not room_id:
                return {'success': False, 'error': 'Room ID required'}
            
            if self.join_user_room(session_id, room_id):
                return {'success': True, 'room_id': room_id}
            else:
                return {'success': False, 'error': 'Failed to join room'}
                
        except Exception as e:
            self.logger.error(f"Error handling join room request: {e}")
            return {'success': False, 'error': str(e)}
    
    def _handle_leave_room_request(self, namespace: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle room leave request
        
        Args:
            namespace: Namespace of the request
            data: Request data containing room_id
            
        Returns:
            Response data
        """
        try:
            session_id = request.sid
            room_id = data.get('room_id')
            
            if not room_id:
                return {'success': False, 'error': 'Room ID required'}
            
            if self.leave_user_room(session_id, room_id):
                return {'success': True, 'room_id': room_id}
            else:
                return {'success': False, 'error': 'Failed to leave room'}
                
        except Exception as e:
            self.logger.error(f"Error handling leave room request: {e}")
            return {'success': False, 'error': str(e)}
    
    def _handle_user_activity(self, namespace: str, data: Dict[str, Any]) -> None:
        """
        Handle user activity events
        
        Args:
            namespace: Namespace of the activity
            data: Activity data
        """
        try:
            session_id = request.sid
            connection = self._connections.get(session_id)
            
            if not connection:
                return
            
            # Broadcast activity to relevant rooms
            activity_data = {
                'user_id': connection.user_id,
                'username': connection.username,
                'activity': data.get('activity', 'unknown'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to user general room
            self.broadcast_to_room('user_general', 'user_activity', activity_data, session_id)
            
        except Exception as e:
            self.logger.error(f"Error handling user activity: {e}")
    
    def _handle_admin_notification(self, namespace: str, data: Dict[str, Any]) -> None:
        """
        Handle admin notification events
        
        Args:
            namespace: Namespace of the notification
            data: Notification data
        """
        try:
            session_id = request.sid
            connection = self._connections.get(session_id)
            
            if not connection or not connection.auth_context.is_admin:
                return
            
            # Broadcast admin notification
            notification_data = {
                'admin_user': connection.username,
                'notification': data.get('notification', {}),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to admin general room
            self.broadcast_to_room('admin_general', 'admin_notification', notification_data, session_id)
            
        except Exception as e:
            self.logger.error(f"Error handling admin notification: {e}")
    
    def _validate_namespace_access(self, auth_context: AuthenticationContext, namespace: str) -> bool:
        """
        Validate user access to namespace
        
        Args:
            auth_context: Authentication context
            namespace: Namespace to validate access for
            
        Returns:
            True if access allowed, False otherwise
        """
        try:
            config = self._namespace_configs.get(namespace)
            if not config:
                return False
            
            # Check admin-only requirement
            if config.admin_only and not auth_context.is_admin:
                return False
            
            # Check required permissions
            if config.required_permissions:
                user_permissions = set(auth_context.permissions)
                if not config.required_permissions.issubset(user_permissions):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating namespace access: {e}")
            return False
    
    def _check_connection_limits(self, user_id: int, namespace: str) -> bool:
        """
        Check if user has exceeded connection limits for namespace
        
        Args:
            user_id: User ID to check
            namespace: Namespace to check limits for
            
        Returns:
            True if within limits, False otherwise
        """
        try:
            config = self._namespace_configs.get(namespace)
            if not config:
                return False
            
            # Count current connections for user in this namespace
            user_sessions = self._user_connections[user_id]
            namespace_sessions = self._namespace_connections[namespace]
            
            current_connections = len(user_sessions.intersection(namespace_sessions))
            
            return current_connections < config.max_connections_per_user
            
        except Exception as e:
            self.logger.error(f"Error checking connection limits: {e}")
            return True  # Allow on error to avoid blocking legitimate users
    
    def _auto_join_default_rooms(self, session_id: str, namespace: str) -> None:
        """
        Auto-join user to default rooms for namespace
        
        Args:
            session_id: User's session ID
            namespace: Namespace to auto-join rooms for
        """
        try:
            # Find auto-join rooms for namespace
            auto_join_rooms = []
            for room_id in self._namespace_rooms[namespace]:
                room_info = self._rooms.get(room_id)
                if room_info and room_info.metadata.get('auto_join', False):
                    auto_join_rooms.append(room_id)
            
            # Join auto-join rooms
            for room_id in auto_join_rooms:
                self.join_user_room(session_id, room_id)
            
            if auto_join_rooms:
                self.logger.debug(f"Auto-joined {len(auto_join_rooms)} rooms for session {session_id}")
                
        except Exception as e:
            self.logger.error(f"Error auto-joining default rooms: {e}")
    
    def _validate_room_access(self, connection: ConnectionInfo, room_info: RoomInfo) -> bool:
        """
        Validate user access to a room
        
        Args:
            connection: User connection info
            room_info: Room information
            
        Returns:
            True if access allowed, False otherwise
        """
        try:
            # Admin users can access all rooms
            if connection.auth_context.is_admin:
                return True
            
            # Check room type restrictions
            if room_info.room_type == 'admin' and not connection.auth_context.is_admin:
                return False
            
            if room_info.room_type == 'security' and not connection.auth_context.is_admin:
                return False
            
            # Check room metadata restrictions
            required_role = room_info.metadata.get('required_role')
            if required_role and connection.role.value != required_role:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating room access: {e}")
            return False
    
    def _wrap_event_handler(self, namespace: str, event_name: str, handler: Callable) -> Callable:
        """
        Wrap event handler with security validation
        
        Args:
            namespace: Namespace of the event
            event_name: Event name
            handler: Original handler function
            
        Returns:
            Wrapped handler function
        """
        def wrapped_handler(*args, **kwargs):
            try:
                session_id = request.sid
                
                # Validate connection exists
                if session_id not in self._connections:
                    self.logger.warning(f"Event {event_name} from unknown session: {session_id}")
                    return {'success': False, 'error': 'Invalid session'}
                
                connection = self._connections[session_id]
                
                # Validate namespace match
                if connection.namespace != namespace:
                    self.logger.warning(f"Namespace mismatch for event {event_name}")
                    return {'success': False, 'error': 'Namespace mismatch'}
                
                # Validate event is allowed
                config = self._namespace_configs[namespace]
                if (config.allowed_events and 
                    event_name not in config.allowed_events):
                    self.logger.warning(f"Event {event_name} not allowed in namespace {namespace}")
                    return {'success': False, 'error': 'Event not allowed'}
                
                # Call original handler
                return handler(*args, **kwargs)
                
            except Exception as e:
                self.logger.error(f"Error in wrapped event handler for {event_name}: {e}")
                return {'success': False, 'error': 'Handler error'}
        
        return wrapped_handler
    
    def cleanup_inactive_connections(self) -> None:
        """
        Clean up inactive connections and rooms
        """
        try:
            current_time = datetime.now(timezone.utc)
            inactive_sessions = []
            
            # Find inactive connections (older than 1 hour with no activity)
            for session_id, connection in self._connections.items():
                if (current_time - connection.connected_at).total_seconds() > 3600:
                    # Check if session is still valid
                    if not self.auth_handler.validate_user_session(connection.user_id, connection.auth_context.session_id):
                        inactive_sessions.append(session_id)
            
            # Clean up inactive sessions
            for session_id in inactive_sessions:
                connection = self._connections[session_id]
                
                # Leave all rooms
                for room_id in list(connection.rooms):
                    self.leave_user_room(session_id, room_id)
                
                # Remove from tracking
                self._user_connections[connection.user_id].discard(session_id)
                self._namespace_connections[connection.namespace].discard(session_id)
                del self._connections[session_id]
                
                self.logger.info(f"Cleaned up inactive connection: {session_id}")
            
            # Clean up empty rooms (except default rooms)
            empty_rooms = []
            for room_id, room_info in self._rooms.items():
                if (len(room_info.members) == 0 and 
                    not room_info.metadata.get('auto_join', False) and
                    room_info.created_by != 0):  # Don't delete system-created rooms
                    empty_rooms.append(room_id)
            
            for room_id in empty_rooms:
                room_info = self._rooms[room_id]
                self._namespace_rooms[room_info.namespace].discard(room_id)
                del self._rooms[room_id]
                self.logger.debug(f"Cleaned up empty room: {room_id}")
            
            if inactive_sessions or empty_rooms:
                self.logger.info(f"Cleanup completed: {len(inactive_sessions)} connections, {len(empty_rooms)} rooms")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """
        Get namespace manager status and statistics
        
        Returns:
            Dictionary containing manager status information
        """
        try:
            return {
                'configured_namespaces': list(self._namespace_configs.keys()),
                'total_connections': len(self._connections),
                'total_rooms': len(self._rooms),
                'connections_by_namespace': {
                    ns: len(sessions) for ns, sessions in self._namespace_connections.items()
                },
                'rooms_by_namespace': {
                    ns: len(rooms) for ns, rooms in self._namespace_rooms.items()
                },
                'unique_users': len(self._user_connections),
                'registered_event_handlers': {
                    ns: list(handlers.keys()) for ns, handlers in self._event_handlers.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting manager status: {e}")
            return {'error': str(e)}
#!/usr/bin/env python3
"""
Consolidated WebSocket Handlers - Phase 3
==========================================

Unified WebSocket handling for all notification types through the
UnifiedNotificationManager. Consolidates dashboard, monitoring, health,
and other notification handlers into a single coherent system.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from flask import current_app
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_login import current_user

from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, NotificationMessage, NotificationType, 
    NotificationPriority, NotificationCategory
)
from models import UserRole

logger = logging.getLogger(__name__)


class ConsolidatedWebSocketHandlers:
    """
    Consolidated WebSocket handlers using UnifiedNotificationManager
    
    Replaces multiple separate handlers with a unified system that handles:
    - Dashboard notifications
    - System monitoring alerts  
    - Health check notifications
    - Performance alerts
    - Storage notifications
    - Platform operation updates
    """
    
    def __init__(self, socketio, notification_manager: UnifiedNotificationManager):
        self.socketio = socketio
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
        
        # Track connected users for efficient message delivery
        self.connected_users = {}
        
        # Register unified handlers
        self.register_unified_handlers()
    
    def register_unified_handlers(self):
        """Register consolidated WebSocket handlers"""
        
        @self.socketio.on('connect', namespace='/')
        def handle_unified_connect(auth):
            """Unified connection handler for all notification types"""
            try:
                # Check if user is authenticated
                if not current_user.is_authenticated:
                    # Allow anonymous connections with limited functionality
                    self.logger.info("Anonymous connection attempt - allowing limited access")
                    
                    # Join anonymous user room
                    join_room("anonymous_users")
                    
                    # Send limited connection confirmation
                    emit('unified_connected', {
                        'status': 'connected',
                        'user_id': None,
                        'pending_messages': 0,
                        'supported_categories': ['public'],
                        'access_level': 'anonymous',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'message': 'Connected with anonymous access - login for full functionality'
                    })
                    
                    self.logger.info("Anonymous user connected successfully")
                    return True
                
                # Handle authenticated users
                user_id = current_user.id
                self.logger.info(f"User {user_id} connecting to unified notifications")
                
                # Join appropriate rooms based on user role and permissions
                self._join_user_rooms(user_id)
                
                # Track connection
                self.connected_users[user_id] = {
                    'connected_at': datetime.now(timezone.utc),
                    'session_id': auth.get('session_id') if auth else None
                }
                
                # Replay pending notifications
                pending_count = self.notification_manager.replay_messages_for_user(user_id)
                
                # Send connection confirmation
                emit('unified_connected', {
                    'status': 'connected',
                    'user_id': user_id,
                    'pending_messages': pending_count,
                    'supported_categories': self._get_user_notification_categories(user_id),
                    'access_level': 'authenticated',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                self.logger.info(f"User {user_id} connected successfully, {pending_count} pending messages")
                return True
                
            except Exception as e:
                self.logger.error(f"Connection error: {e}")
                # Don't return False on error, emit error message instead
                emit('connection_error', {
                    'error': 'Connection failed',
                    'message': 'Unable to establish connection',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                return True  # Allow connection but send error message
        
        @self.socketio.on('disconnect', namespace='/')
        def handle_unified_disconnect():
            """Unified disconnection handler"""
            try:
                if current_user.is_authenticated:
                    user_id = current_user.id
                    
                    # Remove from tracking
                    if user_id in self.connected_users:
                        del self.connected_users[user_id]
                    
                    # Leave all rooms
                    self._leave_user_rooms(user_id)
                    
                    self.logger.info(f"User {user_id} disconnected from unified notifications")
                else:
                    # Handle anonymous user disconnect
                    self.leave_anonymous_rooms()
                    self.logger.info("Anonymous user disconnected from unified notifications")
                
            except Exception as e:
                self.logger.error(f"Disconnection error: {e}")
        
        @self.socketio.on('subscribe_category', namespace='/')
        def handle_category_subscription(data):
            """Subscribe to specific notification categories"""
            try:
                if not current_user.is_authenticated:
                    # Anonymous users can only subscribe to public categories
                    category = data.get('category')
                    if category == 'public':
                        join_room("public_notifications")
                        emit('subscription_confirmed', {
                            'category': category,
                            'status': 'subscribed',
                            'access_level': 'anonymous'
                        })
                        self.logger.info("Anonymous user subscribed to public notifications")
                    else:
                        emit('subscription_error', {
                            'category': category,
                            'error': 'Authentication required for this category'
                        })
                    return
                
                user_id = current_user.id
                category = data.get('category')
                
                if category in self._get_user_notification_categories(user_id):
                    room_name = f"category_{category}_{user_id}"
                    join_room(room_name)
                    
                    emit('subscription_confirmed', {
                        'category': category,
                        'status': 'subscribed',
                        'access_level': 'authenticated'
                    })
                    
                    self.logger.info(f"User {user_id} subscribed to category {category}")
                else:
                    emit('subscription_error', {
                        'category': category,
                        'error': 'Category not allowed for user'
                    })
                    
            except Exception as e:
                self.logger.error(f"Subscription error: {e}")
                emit('subscription_error', {'error': 'Subscription failed'})
        
        @self.socketio.on('request_notification_history', namespace='/')
        def handle_history_request(data):
            """Request notification history"""
            try:
                if not current_user.is_authenticated:
                    # Anonymous users can only request public notification history
                    limit = min(data.get('limit', 10), 25)  # Lower limit for anonymous users
                    category = data.get('category')
                    
                    if category == 'public':
                        # Return empty history for anonymous users (can be enhanced later)
                        emit('notification_history', {
                            'messages': [],
                            'count': 0,
                            'category': category,
                            'access_level': 'anonymous',
                            'message': 'Login to view notification history'
                        })
                    else:
                        emit('history_error', {
                            'error': 'Authentication required to view notification history'
                        })
                    return
                
                user_id = current_user.id
                limit = min(data.get('limit', 50), 100)  # Max 100 messages
                category = data.get('category')
                
                # Get history from notification manager
                history = self.notification_manager.get_user_notification_history(
                    user_id, limit=limit, category=category
                )
                
                emit('notification_history', {
                    'messages': [msg.to_dict() for msg in history],
                    'count': len(history),
                    'category': category,
                    'access_level': 'authenticated'
                })
                
            except Exception as e:
                self.logger.error(f"History request error: {e}")
                emit('history_error', {'error': 'Failed to retrieve history'})
    
    def _join_user_rooms(self, user_id: int):
        """Join user to appropriate notification rooms"""
        try:
            # Join user-specific room
            join_room(f"user_{user_id}")
            
            # Join category-specific rooms based on permissions
            categories = self._get_user_notification_categories(user_id)
            for category in categories:
                join_room(f"category_{category}_{user_id}")
            
            # Join admin rooms if applicable
            if self._is_admin_user(user_id):
                join_room("admin_notifications")
                join_room("system_alerts")
            
        except Exception as e:
            self.logger.error(f"Error joining rooms for user {user_id}: {e}")
    
    def _leave_user_rooms(self, user_id: int):
        """Leave all user rooms"""
        try:
            leave_room(f"user_{user_id}")
            
            categories = self._get_user_notification_categories(user_id)
            for category in categories:
                leave_room(f"category_{category}_{user_id}")
            
            if self._is_admin_user(user_id):
                leave_room("admin_notifications")
                leave_room("system_alerts")
                
        except Exception as e:
            self.logger.error(f"Error leaving rooms for user {user_id}: {e}")
    
    def leave_anonymous_rooms(self):
        """Leave all anonymous user rooms"""
        try:
            leave_room("anonymous_users")
            leave_room("public_notifications")
        except Exception as e:
            self.logger.error(f"Error leaving anonymous rooms: {e}")
    
    def _get_user_notification_categories(self, user_id: int) -> List[str]:
        """Get notification categories user is allowed to receive"""
        try:
            # Base categories for all users
            categories = [
                NotificationCategory.USER.value,
                NotificationCategory.PLATFORM.value,
                NotificationCategory.CAPTION.value,
                NotificationCategory.STORAGE.value
            ]
            
            # Add admin categories if user is admin
            if self._is_admin_user(user_id):
                categories.extend([
                    NotificationCategory.ADMIN.value,
                    NotificationCategory.SYSTEM.value,
                    NotificationCategory.MAINTENANCE.value,
                    NotificationCategory.SECURITY.value,
                    NotificationCategory.MONITORING.value,
                    NotificationCategory.PERFORMANCE.value,
                    NotificationCategory.HEALTH.value,
                    NotificationCategory.DASHBOARD.value
                ])
            
            return categories
            
        except Exception as e:
            self.logger.error(f"Error getting categories for user {user_id}: {e}")
            return [NotificationCategory.USER.value]
    
    def _is_admin_user(self, user_id: int) -> bool:
        """Check if user has admin privileges"""
        # Simplified admin check to avoid database connection issues
        # In production, this would check the actual user role
        return False
    
    def broadcast_notification(self, message: NotificationMessage):
        """Broadcast notification to appropriate WebSocket rooms"""
        try:
            # Determine target rooms based on message properties
            rooms = []
            
            if message.user_id:
                rooms.append(f"user_{message.user_id}")
                rooms.append(f"category_{message.category.value}_{message.user_id}")
            
            # Admin notifications go to admin room
            if message.category in [NotificationCategory.ADMIN, NotificationCategory.SYSTEM]:
                rooms.append("admin_notifications")
            
            # System alerts go to system room
            if message.type == NotificationType.ERROR or message.priority == NotificationPriority.HIGH:
                rooms.append("system_alerts")
            
            # Public notifications go to public room and anonymous users
            if message.category == NotificationCategory.USER:
                rooms.append("public_notifications")
                rooms.append("anonymous_users")
            
            # Broadcast to all relevant rooms
            notification_data = {
                'id': message.id,
                'type': message.type.value,
                'category': message.category.value,
                'title': message.title,
                'message': message.message,
                'priority': message.priority.value,
                'timestamp': message.timestamp.isoformat(),
                'data': message.data
            }
            
            for room in rooms:
                self.socketio.emit('unified_notification', notification_data, room=room)
            
            self.logger.debug(f"Broadcasted notification {message.id} to rooms: {rooms}")
            
        except Exception as e:
            self.logger.error(f"Error broadcasting notification: {e}")
    
    def send_public_notification(self, title: str, message: str, notification_type: str = 'info'):
        """Send a public notification to all connected users including anonymous users"""
        try:
            notification_data = {
                'id': f"public_{datetime.now(timezone.utc).timestamp()}",
                'type': notification_type,
                'category': 'public',
                'title': title,
                'message': message,
                'priority': 'medium',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': {'public': True}
            }
            
            # Send to both public rooms
            self.socketio.emit('unified_notification', notification_data, room="public_notifications")
            self.socketio.emit('unified_notification', notification_data, room="anonymous_users")
            
            self.logger.info(f"Sent public notification: {title}")
            
        except Exception as e:
            self.logger.error(f"Error sending public notification: {e}")
    
    def get_connected_users(self) -> Dict[int, Dict]:
        """Get currently connected users"""
        return self.connected_users.copy()
    
    def is_user_connected(self, user_id: int) -> bool:
        """Check if user is currently connected"""
        return user_id in self.connected_users


def initialize_consolidated_websocket_handlers(app, socketio):
    """Initialize consolidated WebSocket handlers with the app"""
    try:
        # Get unified notification manager from app
        notification_manager = getattr(app, 'unified_notification_manager', None)
        if not notification_manager:
            logger.error("Unified notification manager not found in app")
            return None
        
        # Create consolidated handlers
        handlers = ConsolidatedWebSocketHandlers(socketio, notification_manager)
        
        # Store reference in app for access by other components
        app.consolidated_websocket_handlers = handlers
        
        logger.info("Consolidated WebSocket handlers initialized successfully")
        return handlers
        
    except Exception as e:
        logger.error(f"Failed to initialize consolidated WebSocket handlers: {e}")
        return None

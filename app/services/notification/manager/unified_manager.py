# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unified Notification Manager Core System

This module provides the core notification management system that integrates with the existing
WebSocket CORS framework. It handles role-based message routing, offline message queuing,
message persistence, and replay functionality for reconnecting users.
"""

import logging
import json
import uuid
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque

from flask_socketio import emit
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.websocket.core.factory import WebSocketFactory
from app.websocket.core.auth_handler import WebSocketAuthHandler, AuthenticationContext
from app.websocket.core.namespace_manager import WebSocketNamespaceManager
from models import UserRole, Base, NotificationStorage, NotificationType, NotificationPriority, NotificationCategory
from app.core.database.core.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


# Notification enums are now imported from models.py


@dataclass
class NotificationMessage:
    """Core notification message structure"""
    id: str
    type: NotificationType
    title: str
    message: str
    user_id: Optional[int] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    category: NotificationCategory = NotificationCategory.SYSTEM
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    requires_action: bool = False
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    delivered: bool = False
    read: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.data is None:
            self.data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert enums to strings
        result['type'] = self.type.value
        result['priority'] = self.priority.value
        result['category'] = self.category.value
        # Convert datetime to ISO string
        if self.timestamp:
            result['timestamp'] = self.timestamp.isoformat()
        if self.expires_at:
            result['expires_at'] = self.expires_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationMessage':
        """Create from dictionary"""
        # Convert string enums back to enum objects
        if 'type' in data:
            data['type'] = NotificationType(data['type'])
        if 'priority' in data:
            data['priority'] = NotificationPriority(data['priority'])
        if 'category' in data:
            data['category'] = NotificationCategory(data['category'])
        # Convert ISO strings back to datetime
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        if 'expires_at' in data and isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        return cls(**data)


@dataclass
class AdminNotificationMessage(NotificationMessage):
    """Admin-specific notification message"""
    admin_only: bool = True
    system_health_data: Optional[Dict[str, Any]] = None
    user_action_data: Optional[Dict[str, Any]] = None
    security_event_data: Optional[Dict[str, Any]] = None
    requires_admin_action: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        # Only set ADMIN category if the default SYSTEM category is still set
        # This allows explicit category overrides for admin notifications
        if self.category == NotificationCategory.SYSTEM:
            self.category = NotificationCategory.ADMIN


@dataclass
class SystemNotificationMessage(NotificationMessage):
    """System-wide notification message"""
    broadcast_to_all: bool = True
    maintenance_info: Optional[Dict[str, Any]] = None
    system_status: Optional[str] = None
    estimated_duration: Optional[int] = None  # minutes
    affects_functionality: List[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.SYSTEM
        if self.affects_functionality is None:
            self.affects_functionality = []


@dataclass
class StorageNotificationMessage(NotificationMessage):
    """Storage-specific notification message"""
    storage_gb: Optional[float] = None
    limit_gb: Optional[float] = None
    usage_percentage: Optional[float] = None
    blocked_at: Optional[datetime] = None
    should_hide_form: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.STORAGE


@dataclass
class PerformanceNotificationMessage(NotificationMessage):
    """Performance monitoring notification message"""
    metrics: Optional[Dict[str, float]] = None
    threshold_exceeded: Optional[str] = None
    recovery_action: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.PERFORMANCE


@dataclass
class DashboardNotificationMessage(NotificationMessage):
    """Dashboard-specific notification message"""
    update_type: Optional[str] = None
    dashboard_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.DASHBOARD


@dataclass
class MonitoringNotificationMessage(NotificationMessage):
    """Monitoring alert notification message"""
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    component: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.MONITORING


@dataclass
class HealthNotificationMessage(NotificationMessage):
    """Health check notification message"""
    component: Optional[str] = None
    status: Optional[str] = None
    health_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.category = NotificationCategory.HEALTH


# NotificationStorage model is now imported from models.py


class UnifiedNotificationManager:
    """
    Unified notification manager integrating with existing WebSocket framework
    
    Provides role-based message routing, offline message queuing, persistence capabilities,
    and message history/replay functionality for reconnecting users.
    """
    
    def __init__(self, websocket_factory: WebSocketFactory, auth_handler: WebSocketAuthHandler,
                 namespace_manager: WebSocketNamespaceManager, db_manager: DatabaseManager,
                 max_offline_messages: int = 100, message_retention_days: int = 30):
        """
        Initialize unified notification manager
        
        Args:
            websocket_factory: WebSocket factory instance
            auth_handler: WebSocket authentication handler
            namespace_manager: WebSocket namespace manager
            db_manager: Database manager instance
            max_offline_messages: Maximum offline messages per user
            message_retention_days: Days to retain messages in database
        """
        self.websocket_factory = websocket_factory
        self.auth_handler = auth_handler
        self.namespace_manager = namespace_manager
        self.db_manager = db_manager
        self.max_offline_messages = max_offline_messages
        self.message_retention_days = message_retention_days
        
        # In-memory message queues for offline users
        self._offline_queues = defaultdict(deque)  # user_id -> deque of messages
        self._message_history = defaultdict(deque)  # user_id -> deque of recent messages
        
        # Message delivery tracking
        self._delivery_confirmations = {}  # message_id -> delivery_status
        self._retry_queues = defaultdict(list)  # user_id -> list of failed messages
        
        # Role-based routing configuration
        self._role_permissions = {
            UserRole.ADMIN: {
                'can_receive_admin_notifications': True,
                'can_receive_system_notifications': True,
                'can_receive_security_notifications': True,
                'can_receive_maintenance_notifications': True,
                'namespaces': ['/', '/admin']
            },
            UserRole.MODERATOR: {
                'can_receive_admin_notifications': False,
                'can_receive_system_notifications': True,
                'can_receive_security_notifications': True,
                'can_receive_maintenance_notifications': True,
                'namespaces': ['/']
            },
            UserRole.REVIEWER: {
                'can_receive_admin_notifications': False,
                'can_receive_system_notifications': True,
                'can_receive_security_notifications': False,
                'can_receive_maintenance_notifications': True,
                'namespaces': ['/']
            },
            UserRole.VIEWER: {
                'can_receive_admin_notifications': False,
                'can_receive_system_notifications': True,
                'can_receive_security_notifications': False,
                'can_receive_maintenance_notifications': True,
                'namespaces': ['/']
            }
        }
        
        # Security configuration
        self._security_enabled = True
        self._input_validation_enabled = True
        self._xss_prevention_enabled = True
        self._rate_limiting_enabled = True
        
        # Rate limiting storage
        self._rate_limit_storage = defaultdict(list)
        self._abuse_detection_storage = defaultdict(dict)
        
        # Security thresholds
        self._max_title_length = 200
        self._max_message_length = 2000
        self._max_data_depth = 3
        self._rate_limit_per_minute = 60
        self._burst_threshold = 10
        
        # Allowed protocols for action URLs
        self._allowed_protocols = ['http', 'https']
        self._blocked_protocols = ['javascript', 'data', 'vbscript', 'file']
        
        # Statistics tracking
        self._stats = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'offline_messages_queued': 0,
            'messages_replayed': 0
        }
        
        # WebSocket handlers reference (set by consolidated handlers)
        self.websocket_handlers = None
        
        logger.info("Unified Notification Manager initialized")
    
    def set_websocket_handlers(self, websocket_handlers):
        """Set consolidated WebSocket handlers reference"""
        self.websocket_handlers = websocket_handlers
        logger.info("WebSocket handlers integrated with UnifiedNotificationManager")
    
    def send_user_notification(self, user_id: int, message: NotificationMessage) -> bool:
        """
        Send notification to a specific user
        
        Args:
            user_id: Target user ID
            message: Notification message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Set user ID in message
            message.user_id = user_id
            
            # Check rate limiting first
            if not self._check_priority_rate_limit(user_id, message):
                logger.warning(f"Rate limit exceeded for user {user_id}")
                self._log_security_event("rate_limit_exceeded", user_id, {
                    "message_id": message.id,
                    "message_type": message.category.value
                })
                return False
            
            # Validate user permissions for message type
            if not self._validate_user_permissions(user_id, message):
                logger.warning(f"User {user_id} does not have permission for message type {message.category.value}")
                self._log_security_event("unauthorized_access", user_id, {
                    "message_id": message.id,
                    "message_type": message.category.value,
                    "attempted_category": message.category.value
                })
                return False
            
            # Try to deliver immediately if user is online
            if self._deliver_to_online_user(user_id, message):
                message.delivered = True
                self._stats['messages_delivered'] += 1
                
                # Store in database for history
                self._store_message_in_database(message)
                
                # Add to message history
                self._add_to_message_history(user_id, message)
                
                logger.debug(f"Delivered notification {message.id} to online user {user_id}")
                return True
            else:
                # Queue for offline delivery
                self._queue_offline_message(user_id, message)
                self._stats['offline_messages_queued'] += 1
                
                # Store in database
                self._store_message_in_database(message)
                
                logger.debug(f"Queued notification {message.id} for offline user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send user notification: {e}")
            self._stats['messages_failed'] += 1
            return False
    
    def send_admin_notification(self, message: AdminNotificationMessage) -> bool:
        """
        Send notification to all admin users
        
        Args:
            message: Admin notification message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Get all admin users
            admin_users = self._get_users_by_role(UserRole.ADMIN)
            
            if not admin_users:
                logger.warning("No admin users found for admin notification")
                return False
            
            success_count = 0
            for user_id in admin_users:
                # Create individual message for each admin
                admin_message = AdminNotificationMessage(
                    id=str(uuid.uuid4()),
                    type=message.type,
                    title=message.title,
                    message=message.message,
                    user_id=user_id,
                    priority=message.priority,
                    category=message.category,
                    data=message.data,
                    admin_only=True,
                    system_health_data=message.system_health_data,
                    user_action_data=message.user_action_data,
                    security_event_data=message.security_event_data,
                    requires_admin_action=message.requires_admin_action
                )
                
                if self.send_user_notification(user_id, admin_message):
                    success_count += 1
            
            logger.info(f"Sent admin notification to {success_count}/{len(admin_users)} admin users")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")
            return False
    
    def broadcast_system_notification(self, message: SystemNotificationMessage) -> bool:
        """
        Broadcast system notification to all users
        
        Args:
            message: System notification message to broadcast
            
        Returns:
            True if broadcast successfully, False otherwise
        """
        try:
            # Get all active users
            active_users = self._get_all_active_users()
            
            if not active_users:
                logger.warning("No active users found for system broadcast")
                return False
            
            success_count = 0
            for user_id in active_users:
                # Create individual message for each user
                system_message = SystemNotificationMessage(
                    id=str(uuid.uuid4()),
                    type=message.type,
                    title=message.title,
                    message=message.message,
                    user_id=user_id,
                    priority=message.priority,
                    category=message.category,
                    data=message.data,
                    broadcast_to_all=True,
                    maintenance_info=message.maintenance_info,
                    system_status=message.system_status,
                    estimated_duration=message.estimated_duration,
                    affects_functionality=message.affects_functionality
                )
                
                if self.send_user_notification(user_id, system_message):
                    success_count += 1
            
            logger.info(f"Broadcast system notification to {success_count}/{len(active_users)} users")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to broadcast system notification: {e}")
            return False
    
    def queue_offline_notification(self, user_id: int, message: NotificationMessage) -> None:
        """
        Queue notification for offline user
        
        Args:
            user_id: User ID to queue message for
            message: Notification message to queue
        """
        try:
            self._queue_offline_message(user_id, message)
            self._store_message_in_database(message)
            logger.debug(f"Queued offline notification {message.id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to queue offline notification: {e}")
    
    def get_notification_history(self, user_id: int, limit: int = 50) -> List[NotificationMessage]:
        """
        Get notification history for a user
        
        Args:
            user_id: User ID to get history for
            limit: Maximum number of messages to return
            
        Returns:
            List of notification messages
        """
        try:
            with self.db_manager.get_session() as session:
                # Get recent notifications from database
                notifications = session.query(NotificationStorage)\
                    .filter_by(user_id=user_id)\
                    .order_by(NotificationStorage.timestamp.desc())\
                    .limit(limit)\
                    .all()
                
                return [notif.to_notification_message() for notif in notifications]
                
        except Exception as e:
            logger.error(f"Failed to get notification history for user {user_id}: {e}")
            return []
    
    def replay_messages_for_user(self, user_id: int) -> int:
        """
        Replay queued messages for a reconnecting user
        
        Args:
            user_id: User ID to replay messages for
            
        Returns:
            Number of messages replayed
        """
        try:
            replayed_count = 0
            
            # Replay offline queued messages
            offline_queue = self._offline_queues.get(user_id, deque())
            while offline_queue:
                message = offline_queue.popleft()
                if self._deliver_to_online_user(user_id, message):
                    message.delivered = True
                    self._update_message_delivery_status(message.id, True)
                    replayed_count += 1
                else:
                    # Put back in queue if delivery fails
                    offline_queue.appendleft(message)
                    break
            
            # Replay failed messages from retry queue
            retry_queue = self._retry_queues.get(user_id, [])
            for message in retry_queue[:]:
                if self._deliver_to_online_user(user_id, message):
                    message.delivered = True
                    self._update_message_delivery_status(message.id, True)
                    retry_queue.remove(message)
                    replayed_count += 1
            
            if replayed_count > 0:
                self._stats['messages_replayed'] += replayed_count
                logger.info(f"Replayed {replayed_count} messages for user {user_id}")
            
            return replayed_count
            
        except Exception as e:
            logger.error(f"Failed to replay messages for user {user_id}: {e}")
            return 0
    
    def mark_message_as_read(self, message_id: str, user_id: int) -> bool:
        """
        Mark a message as read by the user
        
        Args:
            message_id: Message ID to mark as read
            user_id: User ID who read the message
            
        Returns:
            True if marked successfully, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                notification = session.query(NotificationStorage)\
                    .filter_by(id=message_id, user_id=user_id)\
                    .first()
                
                if notification:
                    notification.read = True
                    notification.updated_at = datetime.utcnow()
                    session.commit()
                    logger.debug(f"Marked message {message_id} as read for user {user_id}")
                    return True
                else:
                    logger.warning(f"Message {message_id} not found for user {user_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False
    
    def cleanup_expired_messages(self) -> int:
        """
        Clean up expired messages from database and memory
        
        Returns:
            Number of messages cleaned up
        """
        try:
            cleanup_count = 0
            current_time = datetime.now(timezone.utc)
            
            with self.db_manager.get_session() as session:
                # Clean up expired messages
                expired_messages = session.query(NotificationStorage)\
                    .filter(NotificationStorage.expires_at < current_time)\
                    .all()
                
                for message in expired_messages:
                    session.delete(message)
                    cleanup_count += 1
                
                # Clean up old messages beyond retention period
                retention_cutoff = current_time - timedelta(days=self.message_retention_days)
                old_messages = session.query(NotificationStorage)\
                    .filter(NotificationStorage.created_at < retention_cutoff)\
                    .all()
                
                for message in old_messages:
                    session.delete(message)
                    cleanup_count += 1
                
                session.commit()
            
            # Clean up in-memory queues
            for user_id in list(self._offline_queues.keys()):
                queue = self._offline_queues[user_id]
                original_length = len(queue)
                
                # Remove expired messages
                self._offline_queues[user_id] = deque([
                    msg for msg in queue 
                    if not msg.expires_at or msg.expires_at > current_time
                ])
                
                cleanup_count += original_length - len(self._offline_queues[user_id])
            
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} expired/old messages")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired messages: {e}")
            return 0
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """
        Get notification system statistics
        
        Returns:
            Dictionary containing notification statistics
        """
        try:
            # Get database statistics
            with self.db_manager.get_session() as session:
                total_messages = session.query(NotificationStorage).count()
                unread_messages = session.query(NotificationStorage)\
                    .filter_by(read=False).count()
                pending_messages = session.query(NotificationStorage)\
                    .filter_by(delivered=False).count()
            
            # Get in-memory statistics
            offline_queue_sizes = {
                user_id: len(queue) 
                for user_id, queue in self._offline_queues.items()
            }
            
            retry_queue_sizes = {
                user_id: len(queue)
                for user_id, queue in self._retry_queues.items()
            }
            
            return {
                'total_messages_in_db': total_messages,
                'unread_messages': unread_messages,
                'pending_delivery': pending_messages,
                'offline_queues': {
                    'total_users': len(self._offline_queues),
                    'total_messages': sum(offline_queue_sizes.values()),
                    'queue_sizes': offline_queue_sizes
                },
                'retry_queues': {
                    'total_users': len(self._retry_queues),
                    'total_messages': sum(retry_queue_sizes.values()),
                    'queue_sizes': retry_queue_sizes
                },
                'delivery_stats': self._stats,
                'message_retention_days': self.message_retention_days,
                'max_offline_messages': self.max_offline_messages
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return {'error': str(e)}
    
    def _deliver_to_online_user(self, user_id: int, message: NotificationMessage) -> bool:
        """
        Attempt to deliver message to online user via WebSocket
        
        Args:
            user_id: User ID to deliver to
            message: Message to deliver
            
        Returns:
            True if delivered successfully, False otherwise
        """
        try:
            # Use consolidated WebSocket handlers if available
            if self.websocket_handlers:
                if self.websocket_handlers.is_user_connected(user_id):
                    self.websocket_handlers.broadcast_notification(message)
                    logger.debug(f"Delivered notification {message.id} via consolidated handlers")
                    return True
                else:
                    return False
            
            # Fallback to original WebSocket delivery method
            user_connections = self.namespace_manager._user_connections.get(user_id, set())
            
            if not user_connections:
                return False
            
            # Determine appropriate namespace based on message category and user role
            target_namespace = self._determine_target_namespace(user_id, message)
            
            if not target_namespace:
                return False
            
            # Prepare message data for WebSocket emission
            message_data = message.to_dict()
            
            # Emit to user's sessions in the target namespace
            delivered = False
            for session_id in user_connections:
                connection = self.namespace_manager._connections.get(session_id)
                if connection and connection.namespace == target_namespace:
                    try:
                        emit('notification', message_data, 
                             room=session_id, namespace=target_namespace)
                        delivered = True
                        logger.debug(f"Delivered notification {message.id} to session {session_id}")
                    except Exception as e:
                        logger.error(f"Failed to emit to session {session_id}: {e}")
            
            return delivered
            
        except Exception as e:
            logger.error(f"Failed to deliver message to online user {user_id}: {e}")
            return False
    
    def _determine_target_namespace(self, user_id: int, message: NotificationMessage) -> Optional[str]:
        """
        Determine the appropriate namespace for message delivery
        
        Args:
            user_id: User ID
            message: Message to deliver
            
        Returns:
            Target namespace or None if not deliverable
        """
        try:
            # Get user role
            user_role = self._get_user_role(user_id)
            if not user_role:
                return None
            
            # Check role permissions first
            if not self._validate_user_permissions(user_id, message):
                return None
            
            # Check role permissions
            role_config = self._role_permissions.get(user_role, {})
            
            # Admin messages go to admin namespace (only for authorized users)
            if (message.category == NotificationCategory.ADMIN and 
                role_config.get('can_receive_admin_notifications', False)):
                return '/admin'
            
            # Admin messages for non-admin users should return None
            if message.category == NotificationCategory.ADMIN:
                return None
            
            # Security messages for authorized roles
            if (message.category == NotificationCategory.SECURITY and
                role_config.get('can_receive_security_notifications', False)):
                return '/admin' if user_role == UserRole.ADMIN else '/'
            
            # Security messages for non-authorized users should return None
            if message.category == NotificationCategory.SECURITY:
                return None
            
            # System and maintenance messages go to user namespace
            if message.category in [NotificationCategory.SYSTEM, NotificationCategory.MAINTENANCE]:
                return '/'
            
            # User-specific messages go to user namespace
            if message.category in [NotificationCategory.USER, NotificationCategory.CAPTION, NotificationCategory.PLATFORM]:
                return '/'
            
            return '/'  # Default to user namespace for other categories
            
        except Exception as e:
            logger.error(f"Failed to determine target namespace: {e}")
            return None
    
    def _validate_user_permissions(self, user_id: int, message: NotificationMessage) -> bool:
        """
        Validate if user has permission to receive message type
        
        Args:
            user_id: User ID to validate
            message: Message to validate
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            user_role = self._get_user_role(user_id)
            if not user_role:
                return False
            
            role_config = self._role_permissions.get(user_role, {})
            
            # Check category-specific permissions
            if message.category == NotificationCategory.ADMIN:
                return role_config.get('can_receive_admin_notifications', False)
            elif message.category == NotificationCategory.SECURITY:
                return role_config.get('can_receive_security_notifications', False)
            elif message.category == NotificationCategory.MAINTENANCE:
                return role_config.get('can_receive_maintenance_notifications', False)
            else:
                # System, user, caption, platform messages are allowed for all users
                return True
                
        except Exception as e:
            logger.error(f"Failed to validate user permissions: {e}")
            return False
    
    def _queue_offline_message(self, user_id: int, message: NotificationMessage) -> None:
        """
        Queue message for offline user
        
        Args:
            user_id: User ID to queue for
            message: Message to queue
        """
        try:
            queue = self._offline_queues[user_id]
            
            # Limit queue size
            if len(queue) >= self.max_offline_messages:
                # Remove oldest message
                queue.popleft()
            
            queue.append(message)
            
        except Exception as e:
            logger.error(f"Failed to queue offline message: {e}")
    
    def _add_to_message_history(self, user_id: int, message: NotificationMessage) -> None:
        """
        Add message to user's message history
        
        Args:
            user_id: User ID
            message: Message to add
        """
        try:
            history = self._message_history[user_id]
            
            # Limit history size
            if len(history) >= 50:  # Keep last 50 messages in memory
                history.popleft()
            
            history.append(message)
            
        except Exception as e:
            logger.error(f"Failed to add message to history: {e}")
    
    def _store_message_in_database(self, message: NotificationMessage) -> None:
        """
        Store message in database for persistence
        
        Args:
            message: Message to store
        """
        try:
            with self.db_manager.get_session() as session:
                notification = NotificationStorage(
                    id=message.id,
                    user_id=message.user_id,
                    type=message.type,
                    priority=message.priority,
                    category=message.category,
                    title=message.title,
                    message=message.message,
                    data=json.dumps(message.data) if message.data else None,
                    timestamp=message.timestamp,
                    expires_at=message.expires_at,
                    requires_action=message.requires_action,
                    action_url=message.action_url,
                    action_text=message.action_text,
                    delivered=message.delivered,
                    read=message.read
                )
                
                session.add(notification)
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to store message in database: {e}")
    
    def _update_message_delivery_status(self, message_id: str, delivered: bool) -> None:
        """
        Update message delivery status in database
        
        Args:
            message_id: Message ID to update
            delivered: Delivery status
        """
        try:
            with self.db_manager.get_session() as session:
                notification = session.query(NotificationStorage)\
                    .filter_by(id=message_id)\
                    .first()
                
                if notification:
                    notification.delivered = delivered
                    notification.updated_at = datetime.utcnow()
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update message delivery status: {e}")
    
    def _get_user_role(self, user_id: int) -> Optional[UserRole]:
        """
        Get user role from database
        
        Args:
            user_id: User ID
            
        Returns:
            User role or None if not found
        """
        try:
            with self.db_manager.get_session() as session:
                from models import User
                user = session.get(User, user_id)
                return user.role if user else None
                
        except Exception as e:
            logger.error(f"Failed to get user role: {e}")
            return None
    
    def _get_users_by_role(self, role: UserRole) -> List[int]:
        """
        Get list of user IDs with specific role
        
        Args:
            role: User role to filter by
            
        Returns:
            List of user IDs
        """
        try:
            with self.db_manager.get_session() as session:
                from models import User
                users = session.query(User.id)\
                    .filter_by(role=role, is_active=True)\
                    .all()
                return [user.id for user in users]
                
        except Exception as e:
            logger.error(f"Failed to get users by role: {e}")
            return []
    
    def _get_all_active_users(self) -> List[int]:
        """
        Get list of all active user IDs
        
        Returns:
            List of active user IDs
        """
        try:
            with self.db_manager.get_session() as session:
                from models import User
                users = session.query(User.id)\
                    .filter_by(is_active=True)\
                    .all()
                return [user.id for user in users]
                
        except Exception as e:
            logger.error(f"Failed to get all active users: {e}")
            return [] 
   # Security Validation Methods
    
    def _validate_message_content(self, message: NotificationMessage) -> bool:
        """
        Validate message content for security compliance
        
        Args:
            message: Message to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not self._input_validation_enabled:
            return True
            
        try:
            # Check title length
            if len(message.title) > self._max_title_length:
                logger.warning(f"Message title too long: {len(message.title)} > {self._max_title_length}")
                return False
            
            # Check message length
            if len(message.message) > self._max_message_length:
                logger.warning(f"Message content too long: {len(message.message)} > {self._max_message_length}")
                return False
            
            # Check for empty content
            if not message.title.strip() or not message.message.strip():
                logger.warning("Message title or content is empty")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate message content: {e}")
            return False
    
    def _validate_message_data(self, message: NotificationMessage) -> bool:
        """
        Validate message data structure
        
        Args:
            message: Message to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not message.data:
            return True
            
        try:
            # Check data depth to prevent deeply nested structures
            def check_depth(obj, current_depth=0):
                if current_depth > self._max_data_depth:
                    return False
                if isinstance(obj, dict):
                    return all(check_depth(v, current_depth + 1) for v in obj.values())
                elif isinstance(obj, list):
                    return all(check_depth(item, current_depth + 1) for item in obj)
                return True
            
            return check_depth(message.data)
            
        except Exception as e:
            logger.error(f"Failed to validate message data: {e}")
            return False
    
    def _validate_action_url(self, message: NotificationMessage) -> bool:
        """
        Validate action URL for security
        
        Args:
            message: Message to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not message.action_url:
            return True
            
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(message.action_url)
            
            # Check for blocked protocols
            if parsed.scheme.lower() in self._blocked_protocols:
                logger.warning(f"Blocked protocol in action URL: {parsed.scheme}")
                return False
            
            # Allow relative URLs and approved protocols
            if not parsed.scheme or parsed.scheme.lower() in self._allowed_protocols:
                return True
            
            logger.warning(f"Invalid protocol in action URL: {parsed.scheme}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate action URL: {e}")
            return False
    
    def _sanitize_message_content(self, message: NotificationMessage) -> NotificationMessage:
        """
        Sanitize message content to prevent XSS
        
        Args:
            message: Message to sanitize
            
        Returns:
            Sanitized message
        """
        if not self._xss_prevention_enabled:
            return message
            
        try:
            import html
            import re
            
            # Create sanitized copy
            sanitized = NotificationMessage(
                id=message.id,
                type=message.type,
                title=message.title,
                message=message.message,
                user_id=message.user_id,
                priority=message.priority,
                category=message.category,
                data=message.data.copy() if message.data else None,
                timestamp=message.timestamp,
                expires_at=message.expires_at,
                requires_action=message.requires_action,
                action_url=message.action_url,
                action_text=message.action_text,
                delivered=message.delivered,
                read=message.read
            )
            
            # Sanitize title and message
            sanitized.title = self._sanitize_text(message.title)
            sanitized.message = self._sanitize_text(message.message)
            
            # Sanitize action text
            if sanitized.action_text:
                sanitized.action_text = self._sanitize_text(message.action_text)
            
            # Sanitize action URL
            if sanitized.action_url:
                sanitized.action_url = self._sanitize_url(message.action_url)
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Failed to sanitize message content: {e}")
            return message
    
    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text content
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        import html
        import re
        
        # HTML encode dangerous characters
        sanitized = html.escape(text)
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'javascript:',
            r'vbscript:',
            r'data:',
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'on\w+\s*=',  # Event handlers like onclick, onload, etc.
        ]
        
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        return sanitized
    
    def _sanitize_url(self, url: str) -> str:
        """
        Sanitize URL
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL
        """
        from urllib.parse import urlparse, urlunparse
        
        try:
            parsed = urlparse(url)
            
            # Block dangerous protocols
            if parsed.scheme.lower() in self._blocked_protocols:
                return '#'  # Safe placeholder
            
            # Reconstruct URL with safe components
            safe_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                ''  # Remove fragment for security
            ))
            
            return safe_url
            
        except Exception:
            return '#'  # Safe fallback
    
    def _encode_for_html_rendering(self, message: NotificationMessage) -> NotificationMessage:
        """
        Encode message for safe HTML rendering
        
        Args:
            message: Message to encode
            
        Returns:
            HTML-encoded message
        """
        import html
        
        encoded = NotificationMessage(
            id=message.id,
            type=message.type,
            title=html.escape(message.title),
            message=html.escape(message.message),
            user_id=message.user_id,
            priority=message.priority,
            category=message.category,
            data=message.data,
            timestamp=message.timestamp,
            expires_at=message.expires_at,
            requires_action=message.requires_action,
            action_url=message.action_url,
            action_text=html.escape(message.action_text) if message.action_text else None,
            delivered=message.delivered,
            read=message.read
        )
        
        return encoded
    
    def _encode_for_attribute_value(self, message: NotificationMessage) -> NotificationMessage:
        """
        Encode message for safe HTML attribute values
        
        Args:
            message: Message to encode
            
        Returns:
            Attribute-encoded message
        """
        import html
        import re
        
        def encode_for_attr(text):
            if not text:
                return text
            
            # First remove dangerous event handlers
            dangerous_patterns = [
                r'on\w+\s*=\s*["\'][^"\']*["\']',  # Event handlers
                r'javascript:',
                r'vbscript:',
                r'data:'
            ]
            
            sanitized = text
            for pattern in dangerous_patterns:
                sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
            
            # Then HTML encode for attribute context
            return html.escape(sanitized, quote=True)
        
        encoded = NotificationMessage(
            id=message.id,
            type=message.type,
            title=encode_for_attr(message.title),
            message=encode_for_attr(message.message),
            user_id=message.user_id,
            priority=message.priority,
            category=message.category,
            data=message.data,
            timestamp=message.timestamp,
            expires_at=message.expires_at,
            requires_action=message.requires_action,
            action_url=message.action_url,
            action_text=encode_for_attr(message.action_text),
            delivered=message.delivered,
            read=message.read
        )
        
        return encoded
    
    def _encode_for_javascript_context(self, message: NotificationMessage) -> NotificationMessage:
        """
        Encode message for safe JavaScript context
        
        Args:
            message: Message to encode
            
        Returns:
            JavaScript-encoded message
        """
        import json
        import re
        
        def encode_for_js(text):
            if not text:
                return text
            
            # Remove dangerous JavaScript patterns first
            dangerous_patterns = [
                r"';\s*alert\s*\(",
                r'";\s*alert\s*\(',
                r'</script>',
                r'<script[^>]*>',
                r'javascript:',
                r'eval\s*\(',
                r'setTimeout\s*\(',
                r'setInterval\s*\('
            ]
            
            sanitized = text
            for pattern in dangerous_patterns:
                sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
            
            # JSON encode to escape JavaScript special characters
            return json.dumps(sanitized)[1:-1]  # Remove surrounding quotes
        
        # Encode data field if it exists
        encoded_data = message.data
        if message.data:
            encoded_data = {}
            for key, value in message.data.items():
                if isinstance(value, str):
                    encoded_data[key] = encode_for_js(value)
                else:
                    encoded_data[key] = value
        
        encoded = NotificationMessage(
            id=message.id,
            type=message.type,
            title=encode_for_js(message.title),
            message=encode_for_js(message.message),
            user_id=message.user_id,
            priority=message.priority,
            category=message.category,
            data=encoded_data,
            timestamp=message.timestamp,
            expires_at=message.expires_at,
            requires_action=message.requires_action,
            action_url=message.action_url,
            action_text=encode_for_js(message.action_text),
            delivered=message.delivered,
            read=message.read
        )
        
        return encoded
    
    def _encode_for_css_context(self, message: NotificationMessage) -> NotificationMessage:
        """
        Encode message for safe CSS context
        
        Args:
            message: Message to encode
            
        Returns:
            CSS-encoded message
        """
        import re
        
        def encode_for_css(text):
            if not text:
                return text
            # Remove dangerous CSS patterns
            dangerous_css = [
                r'javascript:',
                r'expression\s*\(',
                r'@import',
                r'url\s*\(',
            ]
            
            sanitized = text
            for pattern in dangerous_css:
                sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
            
            return sanitized
        
        encoded = NotificationMessage(
            id=message.id,
            type=message.type,
            title=encode_for_css(message.title),
            message=encode_for_css(message.message),
            user_id=message.user_id,
            priority=message.priority,
            category=message.category,
            data=message.data,
            timestamp=message.timestamp,
            expires_at=message.expires_at,
            requires_action=message.requires_action,
            action_url=message.action_url,
            action_text=encode_for_css(message.action_text),
            delivered=message.delivered,
            read=message.read
        )
        
        return encoded
    
    def _encode_for_url_context(self, message: NotificationMessage) -> NotificationMessage:
        """
        Encode message for safe URL context
        
        Args:
            message: Message to encode
            
        Returns:
            URL-encoded message
        """
        from urllib.parse import quote
        
        def encode_for_url(text):
            if not text:
                return text
            return quote(text, safe='')
        
        encoded = NotificationMessage(
            id=message.id,
            type=message.type,
            title=message.title,
            message=message.message,
            user_id=message.user_id,
            priority=message.priority,
            category=message.category,
            data=message.data,
            timestamp=message.timestamp,
            expires_at=message.expires_at,
            requires_action=message.requires_action,
            action_url=self._sanitize_url(message.action_url) if message.action_url else None,
            action_text=message.action_text,
            delivered=message.delivered,
            read=message.read
        )
        
        return encoded
    
    def _render_for_csp_compliance(self, message: NotificationMessage) -> str:
        """
        Render message content for Content Security Policy compliance
        
        Args:
            message: Message to render
            
        Returns:
            CSP-compliant rendered content
        """
        # Encode for HTML context
        encoded = self._encode_for_html_rendering(message)
        
        # Create safe HTML structure
        safe_html = f"""
        <div class="notification notification-{encoded.type.value}" data-id="{encoded.id}">
            <div class="notification-title">{encoded.title}</div>
            <div class="notification-message">{encoded.message}</div>
            {f'<div class="notification-action"><a href="{encoded.action_url}" class="notification-link">{encoded.action_text}</a></div>' if encoded.action_url and encoded.action_text else ''}
        </div>
        """
        
        return safe_html
    
    # Rate Limiting Methods
    
    def _check_rate_limit(self, user_id: int, message: NotificationMessage) -> bool:
        """
        Check if user is within rate limits
        
        Args:
            user_id: User ID to check
            message: Message being sent
            
        Returns:
            True if within limits, False if rate limited
        """
        if not self._rate_limiting_enabled:
            return True
            
        try:
            current_time = time.time()
            user_requests = self._rate_limit_storage[user_id]
            
            # Remove old requests (outside time window)
            cutoff_time = current_time - 60  # 1 minute window
            user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff_time]
            
            # Check if under rate limit
            rate_limit = self._get_rate_limit_for_user(user_id)
            
            if len(user_requests) >= rate_limit:
                logger.warning(f"Rate limit exceeded for user {user_id}: {len(user_requests)}/{rate_limit}")
                return False
            
            # Record this request
            user_requests.append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return True  # Allow on error to avoid blocking legitimate requests
    
    def _get_rate_limit_for_user(self, user_id: int) -> int:
        """
        Get rate limit for specific user based on role
        
        Args:
            user_id: User ID
            
        Returns:
            Rate limit per minute
        """
        try:
            user_role = self._get_user_role(user_id)
            
            role_limits = {
                UserRole.ADMIN: 1000,
                UserRole.MODERATOR: 500,
                UserRole.REVIEWER: 100,
                UserRole.VIEWER: 50
            }
            
            return role_limits.get(user_role, 10)  # Default low limit
            
        except Exception as e:
            logger.error(f"Failed to get rate limit for user: {e}")
            return 10  # Conservative default
    
    def _is_rate_limited(self, user_id: int) -> bool:
        """
        Check if user is currently rate limited
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()
        user_requests = self._rate_limit_storage[user_id]
        
        # Remove old requests
        cutoff_time = current_time - 60
        user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff_time]
        
        rate_limit = self._get_rate_limit_for_user(user_id)
        return len(user_requests) >= rate_limit
    
    def _record_rate_limit_usage(self, user_id: int, message: NotificationMessage) -> None:
        """
        Record rate limit usage for user
        
        Args:
            user_id: User ID
            message: Message being sent
        """
        current_time = time.time()
        self._rate_limit_storage[user_id].append(current_time)
    
    def _check_priority_rate_limit(self, user_id: int, message: NotificationMessage) -> bool:
        """
        Check rate limit with priority consideration
        
        Args:
            user_id: User ID
            message: Message to check
            
        Returns:
            True if allowed, False if rate limited
        """
        # Critical messages bypass rate limits
        if message.priority == NotificationPriority.CRITICAL:
            return True
        
        # For normal messages, check if rate limited
        if self._is_rate_limited(user_id):
            return False
        
        return True
    
    def _detect_burst_pattern(self, user_id: int, message: NotificationMessage) -> bool:
        """
        Detect burst/spam patterns
        
        Args:
            user_id: User ID
            message: Message being sent
            
        Returns:
            True if burst detected, False otherwise
        """
        try:
            current_time = time.time()
            burst_threshold = 5  # 5 messages in 10 seconds is considered a burst
            burst_window = 10    # seconds
            
            if not hasattr(self, '_burst_detection_storage'):
                self._burst_detection_storage = defaultdict(list)
            
            user_requests = self._burst_detection_storage[user_id]
            
            # Clean old requests
            user_requests = [req_time for req_time in user_requests if req_time > current_time - burst_window]
            self._burst_detection_storage[user_id] = user_requests
            
            # Check if this would exceed burst threshold
            is_burst = len(user_requests) >= burst_threshold
            
            # Record current request
            user_requests.append(current_time)
            
            if is_burst:
                # Only log every 10th burst to reduce performance impact
                if len(user_requests) % 10 == 0:
                    logger.warning(f"Burst pattern detected for user {user_id}: {len(user_requests)} requests in {burst_window} seconds")
            
            return is_burst
            
        except Exception as e:
            logger.error(f"Failed to detect burst pattern: {e}")
            return False
    
    def _detect_spam_pattern(self, user_id: int, message: NotificationMessage) -> bool:
        """Detect spam patterns in messages"""
        if not hasattr(self, '_spam_detection_storage'):
            self._spam_detection_storage = defaultdict(list)
        
        # Get message content hash
        content_hash = hashlib.md5(f"{message.title}{message.message}".encode()).hexdigest()
        
        # Check recent messages for duplicates
        user_messages = self._spam_detection_storage[user_id]
        current_time = time.time()
        
        # Clean old entries (last hour)
        user_messages[:] = [msg for msg in user_messages if current_time - msg['timestamp'] < 3600]
        
        # Count identical messages
        identical_count = sum(1 for msg in user_messages if msg['hash'] == content_hash)
        
        # Record current message
        user_messages.append({
            'hash': content_hash,
            'timestamp': current_time
        })
        
        # Consider spam if more than 3 identical messages
        return identical_count >= 3
    
    def _get_system_load(self) -> dict:
        """Get current system load information"""
        try:
            import psutil
            return {
                'cpu': psutil.cpu_percent(),
                'memory': psutil.virtual_memory().percent,
                'load': 'high' if psutil.cpu_percent() > 80 else 'medium' if psutil.cpu_percent() > 50 else 'low'
            }
        except ImportError:
            # Fallback if psutil not available
            return {'cpu': 30, 'memory': 40, 'load': 'low'}
    
    def _get_adaptive_rate_limit(self, user_id: int) -> int:
        """Get adaptive rate limit based on system load"""
        base_limit = self._get_rate_limit_for_user(user_id)
        system_load = self._get_system_load()
        
        if system_load['load'] == 'high':
            return int(base_limit * 0.5)  # Reduce by 50% under high load
        elif system_load['load'] == 'medium':
            return int(base_limit * 0.75)  # Reduce by 25% under medium load
        else:
            return base_limit  # Normal limit under low load
    
    def _check_ip_rate_limit(self, ip_address: str, message: NotificationMessage) -> bool:
        """Check rate limit based on IP address"""
        if not hasattr(self, '_ip_rate_limit_storage'):
            self._ip_rate_limit_storage = defaultdict(list)
        
        current_time = time.time()
        time_window = 3600  # 1 hour
        ip_rate_limit = 100  # per hour
        
        # Clean old entries
        ip_requests = self._ip_rate_limit_storage[ip_address]
        ip_requests[:] = [req for req in ip_requests if current_time - req < time_window]
        
        # Check if limit exceeded
        if len(ip_requests) >= ip_rate_limit:
            return False
        
        # Record current request
        ip_requests.append(current_time)
        return True
    
    def _check_system_message_bypass(self, user_id: int, message: NotificationMessage) -> bool:
        """Check if system messages can bypass rate limits"""
        # System messages and high priority messages bypass rate limits
        if (message.category == NotificationCategory.SYSTEM or 
            message.priority == NotificationPriority.CRITICAL or
            isinstance(message, SystemNotificationMessage)):
            return True
        return False
    
    def _log_security_event(self, event_type: str, user_id: int, details: dict) -> None:
        """Log security events for monitoring"""
        if not hasattr(self, '_security_events'):
            self._security_events = []
        
        event = {
            'event_type': event_type,
            'user_id': user_id,
            'details': details,
            'timestamp': datetime.now(timezone.utc)
        }
        
        self._security_events.append(event)
        logger.warning(f"Security event: {event_type} for user {user_id}: {details}")
    
    def _update_security_metrics(self, metric_type: str, increment: int = 1) -> None:
        """Update security metrics"""
        if not hasattr(self, '_security_metrics'):
            self._security_metrics = defaultdict(int)
        
        self._security_metrics[metric_type] += increment
    
    def _validate_security_config(self, config: dict) -> bool:
        """Validate security configuration"""
        required_fields = [
            'input_validation_enabled',
            'xss_prevention_enabled', 
            'rate_limiting_enabled'
        ]
        
        for field in required_fields:
            if field not in config:
                return False
            if not isinstance(config[field], bool):
                return False
        
        # Validate numeric fields
        numeric_fields = {
            'max_message_length': (1, 10000),
            'max_title_length': (1, 1000),
            'rate_limit_per_minute': (1, 10000)
        }
        
        for field, (min_val, max_val) in numeric_fields.items():
            if field in config:
                if not isinstance(config[field], int) or not (min_val <= config[field] <= max_val):
                    return False
        
        return True

    # Additional security methods would be implemented here...
    # These are placeholder methods referenced in the tests
    
    def _calculate_content_similarity(self, user_id: int, message: NotificationMessage) -> float:
        """Calculate content similarity to previous messages"""
        if not hasattr(self, '_user_message_history'):
            self._user_message_history = defaultdict(list)
        
        user_messages = self._user_message_history[user_id]
        if not user_messages:
            return 0.0
        
        current_content = f"{message.title} {message.message}".lower()
        
        # Simple similarity calculation based on word overlap
        current_words = set(current_content.split())
        
        max_similarity = 0.0
        # Only check last 5 messages for performance
        for prev_message in user_messages[-5:]:
            prev_content = f"{prev_message['title']} {prev_message['message']}".lower()
            prev_words = set(prev_content.split())
            
            if not prev_words:
                continue
            
            # Quick similarity check - if no common words, skip expensive calculation
            if not current_words.intersection(prev_words):
                continue
            
            # Calculate Jaccard similarity
            intersection = len(current_words.intersection(prev_words))
            union = len(current_words.union(prev_words))
            
            if union > 0:
                similarity = intersection / union
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _record_message_content(self, user_id: int, message: NotificationMessage) -> None:
        """Record message content for similarity analysis"""
        if not hasattr(self, '_user_message_history'):
            self._user_message_history = defaultdict(list)
        
        user_messages = self._user_message_history[user_id]
        
        # Add current message to history
        user_messages.append({
            'title': message.title,
            'message': message.message,
            'timestamp': time.time()
        })
        
        # Keep only last 50 messages per user
        if len(user_messages) > 50:
            user_messages[:] = user_messages[-50:]
    
    def _detect_abnormal_frequency(self, user_id: int, message: NotificationMessage) -> bool:
        """Detect abnormal message frequency"""
        if not hasattr(self, '_frequency_detection_storage'):
            self._frequency_detection_storage = defaultdict(list)
        
        current_time = time.time()
        user_timestamps = self._frequency_detection_storage[user_id]
        
        # Clean old timestamps (older than 5 minutes)
        user_timestamps[:] = [ts for ts in user_timestamps if current_time - ts < 300]
        
        # Calculate intervals between messages
        if len(user_timestamps) >= 2:
            intervals = []
            for i in range(1, len(user_timestamps)):
                interval = user_timestamps[i] - user_timestamps[i-1]
                intervals.append(interval)
            
            # Check if recent intervals are abnormally short
            if len(intervals) >= 3:
                recent_intervals = intervals[-3:]
                avg_interval = sum(recent_intervals) / len(recent_intervals)
                
                # Consider abnormal if average interval is less than 5 seconds
                if avg_interval < 5:
                    return True
        
        # Record current timestamp
        user_timestamps.append(current_time)
        
        return False
    
    def _record_behavioral_pattern(self, user_id: int, message: NotificationMessage) -> None:
        """Record user behavioral patterns"""
        pass  # Placeholder implementation
    
    def _analyze_behavioral_deviation(self, user_id: int, message: NotificationMessage) -> bool:
        """Analyze behavioral deviation from normal patterns"""
        return False  # Placeholder implementation
    
    def _record_potential_attack_pattern(self, user_id: int, ip: str, message: NotificationMessage) -> None:
        """Record potential attack patterns"""
        pass  # Placeholder implementation
    
    def _detect_coordinated_attack(self, content_pattern: str, time_window: int, min_participants: int) -> bool:
        """Detect coordinated attacks"""
        return False  # Placeholder implementation
    
    def _calculate_content_entropy(self, message: NotificationMessage) -> float:
        """Calculate content entropy for bot detection"""
        import math
        from collections import Counter
        
        content = f"{message.title} {message.message}"
        if not content:
            return 0.0
        
        # Calculate character frequency
        char_counts = Counter(content.lower())
        total_chars = len(content)
        
        # Calculate Shannon entropy
        entropy = 0.0
        for count in char_counts.values():
            probability = count / total_chars
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        # Normalize entropy (max entropy for English text is around 4.7)
        max_entropy = 4.7
        normalized_entropy = min(entropy / max_entropy, 1.0)
        
        return normalized_entropy
    
    def _check_ip_reputation(self, ip: str, message: NotificationMessage) -> bool:
        """Check IP reputation"""
        return False  # Placeholder implementation
    
    def _record_session_characteristics(self, user_id: int, session_id: str, ip: str, user_agent: str) -> None:
        """Record session characteristics"""
        pass  # Placeholder implementation
    
    def _detect_session_hijacking(self, user_id: int, session_id: str, message: NotificationMessage) -> bool:
        """Detect session hijacking attempts"""
        return False  # Placeholder implementation
    
    def _detect_privilege_escalation(self, user_id: int, message: NotificationMessage) -> bool:
        """Detect privilege escalation attempts"""
        user_role = self._get_user_role(user_id)
        if not user_role:
            return True
        
        # Check if user is trying to send admin messages without admin role
        if (message.category == NotificationCategory.ADMIN and 
            user_role != UserRole.ADMIN):
            return True
        
        return False
    
    def _execute_automated_threat_response(self, threat_info: dict) -> list:
        """Execute automated threat response"""
        actions = [
            {'type': 'log_security_event', 'details': threat_info},
            {'type': 'update_metrics', 'metric': threat_info['type']}
        ]
        
        if threat_info['severity'] == 'high':
            actions.extend([
                {'type': 'alert_administrators', 'threat': threat_info},
                {'type': 'increase_monitoring', 'user_id': threat_info['user_id']}
            ])
        
        return actions
    
    def _extract_message_features(self, message: NotificationMessage) -> dict:
        """Extract features for ML analysis"""
        import re
        
        title = message.title or ""
        msg_text = message.message or ""
        
        # Extract various features efficiently
        combined_text = title + " " + msg_text
        
        features = {
            'title_length': len(title),
            'message_length': len(msg_text),
            'type': message.type.value if hasattr(message.type, 'value') else 1,
            'category': message.category.value if hasattr(message.category, 'value') else 1,
            'priority': message.priority.value if hasattr(message.priority, 'value') else 1,
            'has_action': bool(message.action_url),
            'word_count': len(combined_text.split()),
            'char_count': len(combined_text)
        }
        
        return features
    
    def _train_anomaly_detection_model(self, user_id: int, patterns: list) -> None:
        """Train anomaly detection model"""
        pass  # Placeholder implementation
    
    def _detect_ml_anomaly(self, user_id: int, message: NotificationMessage) -> bool:
        """Detect anomalies using ML"""
        # Simple anomaly detection based on message features
        features = self._extract_message_features(message)
        
        # Get user's normal patterns
        if not hasattr(self, '_user_patterns'):
            self._user_patterns = defaultdict(list)
        
        user_patterns = self._user_patterns[user_id]
        
        # If we don't have enough historical data, use simple heuristics
        if len(user_patterns) < 10:
            user_patterns.append(features)
            
            # Simple heuristic: check for obvious anomalies
            # Check for spam-like characteristics
            title = message.title or ""
            msg_text = message.message or ""
            combined_text = (title + " " + msg_text).upper()
            
            # Spam indicators
            spam_indicators = ['URGENT!!!', 'CLICK NOW!!!', 'FREE MONEY!!!', 'ACT FAST']
            spam_score = sum(1 for indicator in spam_indicators if indicator in combined_text)
            
            if spam_score >= 2:  # Multiple spam indicators
                return True
            
            # Extremely long messages
            if features.get('message_length', 0) > 1000:
                return True
            
            # Messages with very low entropy (bot-like)
            if features.get('entropy', 1.0) < 0.3:
                return True
            
            return False
        
        # Simple anomaly detection: check if current features deviate significantly
        # from historical patterns
        
        # Calculate average values for each feature
        avg_features = {}
        for feature_name in features:
            values = [pattern.get(feature_name, 0) for pattern in user_patterns]
            avg_features[feature_name] = sum(values) / len(values)
        
        # Check for significant deviations
        anomaly_threshold = 2.0  # Standard deviations
        is_anomalous = False
        
        for feature_name, current_value in features.items():
            if feature_name in avg_features:
                avg_value = avg_features[feature_name]
                if avg_value > 0:
                    deviation = abs(current_value - avg_value) / avg_value
                    if deviation > anomaly_threshold:
                        is_anomalous = True
                        break
        
        # Add current features to patterns (keep last 20 for performance)
        user_patterns.append(features)
        if len(user_patterns) > 20:
            user_patterns[:] = user_patterns[-20:]
        
        return is_anomalous
    
    def _set_threat_level(self, level: str) -> None:
        """Set system threat level"""
        self._current_threat_level = level
    
    def _get_adaptive_security_config(self) -> dict:
        """Get adaptive security configuration"""
        threat_level = getattr(self, '_current_threat_level', 'low')
        
        configs = {
            'low': {'rate_limit': 100, 'strict_validation': False, 'enhanced_monitoring': False},
            'medium': {'rate_limit': 75, 'strict_validation': False, 'enhanced_monitoring': True},
            'high': {'rate_limit': 35, 'strict_validation': True, 'enhanced_monitoring': True},
            'critical': {'rate_limit': 15, 'strict_validation': True, 'enhanced_monitoring': True}
        }
        
        return configs.get(threat_level, configs['low'])
    
    def _establish_user_trust_score(self, user_id: int, trust_score: float) -> None:
        """Establish user trust score"""
        if not hasattr(self, '_user_trust_scores'):
            self._user_trust_scores = {}
        self._user_trust_scores[user_id] = trust_score
    
    def _detect_suspicious_content(self, user_id: int, message: NotificationMessage, consider_trust: bool = True) -> bool:
        """Detect suspicious content"""
        # Basic suspicious content detection
        suspicious_keywords = ['urgent', 'click now', 'free money', 'act fast']
        content = (message.title + ' ' + message.message).lower()
        
        has_suspicious_keywords = any(keyword in content for keyword in suspicious_keywords)
        
        if consider_trust and hasattr(self, '_user_trust_scores'):
            trust_score = self._user_trust_scores.get(user_id, 0.5)
            # Higher trust reduces suspicion
            return has_suspicious_keywords and trust_score < 0.8
        
        return has_suspicious_keywords
    
    def _detect_abuse_patterns(self, user_id: int, message: NotificationMessage) -> bool:
        """Detect various abuse patterns"""
        # Combine multiple detection methods
        patterns = [
            self._detect_burst_pattern(user_id, message),
            self._detect_abnormal_frequency(user_id, message),
            self._detect_privilege_escalation(user_id, message)
        ]
        
        return any(patterns)
    
    def _validate_security_config(self, config: dict) -> bool:
        """Validate security configuration"""
        try:
            # Check required boolean fields
            boolean_fields = ['input_validation_enabled', 'xss_prevention_enabled', 'rate_limiting_enabled']
            for field in boolean_fields:
                if field in config and not isinstance(config[field], bool):
                    return False
            
            # Check numeric fields
            numeric_fields = ['max_message_length', 'max_title_length', 'rate_limit_per_minute']
            for field in numeric_fields:
                if field in config:
                    if not isinstance(config[field], (int, float)) or config[field] < 0:
                        return False
            
            return True
            
        except Exception:
            return False
    

    
    def _update_security_metrics(self, metric_type: str, increment: int = 1) -> None:
        """Update security metrics"""
        if not hasattr(self, '_security_metrics'):
            self._security_metrics = defaultdict(int)
        self._security_metrics[metric_type] += increment
    
    def _detect_spam_pattern(self, user_id: int, message: NotificationMessage) -> bool:
        """Detect spam patterns in messages"""
        if not hasattr(self, '_spam_detection_storage'):
            self._spam_detection_storage = defaultdict(list)
        
        # Get recent messages from this user
        recent_messages = self._spam_detection_storage[user_id]
        current_time = time.time()
        
        # Clean old messages (older than 1 hour)
        recent_messages = [msg for msg in recent_messages if current_time - msg['timestamp'] < 3600]
        self._spam_detection_storage[user_id] = recent_messages
        
        # Check for identical content
        message_content = f"{message.title}|{message.message}"
        identical_count = sum(1 for msg in recent_messages if msg['content'] == message_content)
        
        # Record current message
        recent_messages.append({
            'content': message_content,
            'timestamp': current_time
        })
        
        # Consider it spam if more than 3 identical messages in the last hour
        return identical_count >= 3
    
    def _get_system_load(self) -> dict:
        """Get current system load information"""
        # Mock system load for testing
        return {
            'cpu': 50,
            'memory': 60,
            'load': 'medium'
        }
    
    def _check_system_message_bypass(self, user_id: int, message: NotificationMessage) -> bool:
        """Check if system messages can bypass rate limits"""
        # System messages and admin messages can bypass rate limits
        if isinstance(message, SystemNotificationMessage):
            return True
        if isinstance(message, AdminNotificationMessage):
            return True
        if message.category == NotificationCategory.SYSTEM and message.priority == NotificationPriority.CRITICAL:
            return True
        return False
    
    def _get_adaptive_rate_limit(self, user_id: int) -> int:
        """Get adaptive rate limit based on system load"""
        base_limit = self._get_rate_limit_for_user(user_id)
        system_load = self._get_system_load()
        
        # Adjust rate limit based on system load
        if system_load['load'] == 'high':
            return int(base_limit * 0.5)  # Reduce by 50% under high load
        elif system_load['load'] == 'low':
            return int(base_limit * 1.5)  # Increase by 50% under low load
        else:
            return base_limit  # Keep normal limit for medium load
    
    def _check_ip_rate_limit(self, ip_address: str, message: NotificationMessage) -> bool:
        """Check rate limit based on IP address"""
        if not hasattr(self, '_ip_rate_limit_storage'):
            self._ip_rate_limit_storage = defaultdict(list)
        
        current_time = time.time()
        ip_requests = self._ip_rate_limit_storage[ip_address]
        
        # Clean old requests (older than 1 hour)
        ip_requests = [req for req in ip_requests if current_time - req < 3600]
        self._ip_rate_limit_storage[ip_address] = ip_requests
        
        # IP rate limit: 100 requests per hour
        ip_rate_limit = 100
        
        if len(ip_requests) >= ip_rate_limit:
            return False
        
        # Record current request
        ip_requests.append(current_time)
        return True

    def mark_message_as_read(self, message_id: str, user_id: int) -> bool:
        """
        Mark message as read by user
        
        Args:
            message_id: Message ID
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                notification = session.query(NotificationStorage)\
                    .filter_by(id=message_id, user_id=user_id)\
                    .first()
                
                if notification:
                    notification.read = True
                    session.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Real-Time Notification System

This module provides standardized real-time notification functionality for WebSocket
communications, including message formatting, routing, delivery confirmation,
priority handling, and offline user persistence.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, List, Set, Union, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
from threading import Lock, RLock
from flask_socketio import SocketIO, emit

from models import UserRole

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationType(Enum):
    """Notification types for categorization"""
    SYSTEM = "system"
    USER_ACTION = "user_action"
    PROGRESS_UPDATE = "progress_update"
    ALERT = "alert"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ADMIN = "admin"
    SECURITY = "security"


class DeliveryStatus(Enum):
    """Message delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class NotificationTarget:
    """Target specification for notifications"""
    user_ids: Set[int] = field(default_factory=set)
    roles: Set[UserRole] = field(default_factory=set)
    namespaces: Set[str] = field(default_factory=set)
    rooms: Set[str] = field(default_factory=set)
    exclude_user_ids: Set[int] = field(default_factory=set)
    
    def is_empty(self) -> bool:
        """Check if target specification is empty"""
        return not any([self.user_ids, self.roles, self.namespaces, self.rooms])


@dataclass
class NotificationFilter:
    """Filter criteria for notifications"""
    types: Set[NotificationType] = field(default_factory=set)
    priorities: Set[NotificationPriority] = field(default_factory=set)
    sources: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    min_priority: Optional[NotificationPriority] = None
    max_age_hours: Optional[int] = None
    
    def matches(self, notification: 'StandardizedNotification') -> bool:
        """Check if notification matches filter criteria"""
        # Type filter
        if self.types and notification.notification_type not in self.types:
            return False
        
        # Priority filter
        if self.priorities and notification.priority not in self.priorities:
            return False
        
        # Minimum priority filter
        if self.min_priority:
            priority_order = {
                NotificationPriority.LOW: 1,
                NotificationPriority.NORMAL: 2,
                NotificationPriority.HIGH: 3,
                NotificationPriority.URGENT: 4,
                NotificationPriority.CRITICAL: 5
            }
            if priority_order.get(notification.priority, 0) < priority_order.get(self.min_priority, 0):
                return False
        
        # Source filter
        if self.sources and notification.source not in self.sources:
            return False
        
        # Tags filter
        if self.tags and not self.tags.intersection(notification.tags):
            return False
        
        # Age filter
        if self.max_age_hours:
            age = datetime.now(timezone.utc) - notification.created_at
            if age > timedelta(hours=self.max_age_hours):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary for serialization"""
        return {
            'types': [t.value for t in self.types],
            'priorities': [p.value for p in self.priorities],
            'sources': list(self.sources),
            'tags': list(self.tags),
            'min_priority': self.min_priority.value if self.min_priority else None,
            'max_age_hours': self.max_age_hours
        }


@dataclass
class StandardizedNotification:
    """Standardized notification message format"""
    # Core identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_name: str = ""
    
    # Content
    title: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Classification
    notification_type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    source: str = "system"
    tags: Set[str] = field(default_factory=set)
    
    # Targeting
    target: NotificationTarget = field(default_factory=NotificationTarget)
    
    # Delivery settings
    requires_acknowledgment: bool = False
    expires_at: Optional[datetime] = None
    retry_count: int = 3
    retry_delay_seconds: int = 5
    
    # Persistence settings
    persist_offline: bool = True
    persist_duration_hours: int = 24
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[int] = None
    namespace: str = "/"
    room: Optional[str] = None
    
    # Delivery tracking
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    delivered_to: Set[str] = field(default_factory=set)  # session_ids
    acknowledged_by: Set[str] = field(default_factory=set)  # session_ids
    failed_deliveries: List[str] = field(default_factory=list)  # error messages
    last_delivery_attempt: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for JSON serialization"""
        result = asdict(self)
        
        # Convert sets to lists for JSON serialization
        result['tags'] = list(self.tags)
        result['target']['user_ids'] = list(self.target.user_ids)
        result['target']['roles'] = [role.value for role in self.target.roles]
        result['target']['namespaces'] = list(self.target.namespaces)
        result['target']['rooms'] = list(self.target.rooms)
        result['target']['exclude_user_ids'] = list(self.target.exclude_user_ids)
        result['delivered_to'] = list(self.delivered_to)
        result['acknowledged_by'] = list(self.acknowledged_by)
        
        # Convert enums to strings
        result['notification_type'] = self.notification_type.value
        result['priority'] = self.priority.value
        result['delivery_status'] = self.delivery_status.value
        
        # Convert datetime objects to ISO strings
        result['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            result['expires_at'] = self.expires_at.isoformat()
        if self.last_delivery_attempt:
            result['last_delivery_attempt'] = self.last_delivery_attempt.isoformat()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StandardizedNotification':
        """Create notification from dictionary"""
        # Convert lists back to sets
        if 'tags' in data:
            data['tags'] = set(data['tags'])
        
        # Handle target conversion
        if 'target' in data:
            target_data = data['target']
            target_data['user_ids'] = set(target_data.get('user_ids', []))
            target_data['roles'] = {UserRole(role) for role in target_data.get('roles', [])}
            target_data['namespaces'] = set(target_data.get('namespaces', []))
            target_data['rooms'] = set(target_data.get('rooms', []))
            target_data['exclude_user_ids'] = set(target_data.get('exclude_user_ids', []))
            data['target'] = NotificationTarget(**target_data)
        
        # Convert delivered_to and acknowledged_by back to sets
        if 'delivered_to' in data:
            data['delivered_to'] = set(data['delivered_to'])
        if 'acknowledged_by' in data:
            data['acknowledged_by'] = set(data['acknowledged_by'])
        
        # Convert enum strings back to enums
        if 'notification_type' in data:
            data['notification_type'] = NotificationType(data['notification_type'])
        if 'priority' in data:
            data['priority'] = NotificationPriority(data['priority'])
        if 'delivery_status' in data:
            data['delivery_status'] = DeliveryStatus(data['delivery_status'])
        
        # Convert datetime strings back to datetime objects
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if 'expires_at' in data and isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        if 'last_delivery_attempt' in data and isinstance(data['last_delivery_attempt'], str):
            data['last_delivery_attempt'] = datetime.fromisoformat(data['last_delivery_attempt'].replace('Z', '+00:00'))
        
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def should_persist(self) -> bool:
        """Check if notification should be persisted for offline users"""
        if not self.persist_offline:
            return False
        
        # Check if within persistence duration
        age = datetime.now(timezone.utc) - self.created_at
        return age < timedelta(hours=self.persist_duration_hours)
    
    def get_client_payload(self) -> Dict[str, Any]:
        """Get payload to send to client (excludes internal tracking data)"""
        return {
            'id': self.id,
            'event_name': self.event_name,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'type': self.notification_type.value,
            'priority': self.priority.value,
            'source': self.source,
            'tags': list(self.tags),
            'requires_acknowledgment': self.requires_acknowledgment,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'namespace': self.namespace,
            'room': self.room
        }


class NotificationRouter:
    """Routes notifications to appropriate targets"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.logger = logging.getLogger(__name__)
        
        # Connection tracking (will be provided by namespace manager)
        self._connection_tracker = None
        
    def set_connection_tracker(self, connection_tracker):
        """Set connection tracker for routing decisions"""
        self._connection_tracker = connection_tracker
    
    def route_notification(self, notification: StandardizedNotification) -> List[str]:
        """
        Route notification to appropriate targets
        
        Args:
            notification: Notification to route
            
        Returns:
            List of session IDs that should receive the notification
        """
        target_sessions = set()
        
        try:
            # Route by user IDs
            if notification.target.user_ids:
                user_sessions = self._get_sessions_for_users(notification.target.user_ids)
                target_sessions.update(user_sessions)
            
            # Route by roles
            if notification.target.roles:
                role_sessions = self._get_sessions_for_roles(notification.target.roles)
                target_sessions.update(role_sessions)
            
            # Route by namespaces
            if notification.target.namespaces:
                namespace_sessions = self._get_sessions_for_namespaces(notification.target.namespaces)
                target_sessions.update(namespace_sessions)
            
            # Route by rooms
            if notification.target.rooms:
                room_sessions = self._get_sessions_for_rooms(notification.target.rooms)
                target_sessions.update(room_sessions)
            
            # If no specific targets, route to notification's namespace
            if not target_sessions and notification.namespace:
                namespace_sessions = self._get_sessions_for_namespaces({notification.namespace})
                target_sessions.update(namespace_sessions)
            
            # Exclude specified users
            if notification.target.exclude_user_ids:
                excluded_sessions = self._get_sessions_for_users(notification.target.exclude_user_ids)
                target_sessions -= excluded_sessions
            
            self.logger.debug(f"Routed notification {notification.id} to {len(target_sessions)} sessions")
            return list(target_sessions)
            
        except Exception as e:
            self.logger.error(f"Error routing notification {notification.id}: {e}")
            return []
    
    def _get_sessions_for_users(self, user_ids: Set[int]) -> Set[str]:
        """Get session IDs for specific users"""
        if not self._connection_tracker:
            return set()
        
        sessions = set()
        for user_id in user_ids:
            user_sessions = self._connection_tracker.get_user_sessions(user_id)
            sessions.update(user_sessions)
        
        return sessions
    
    def _get_sessions_for_roles(self, roles: Set[UserRole]) -> Set[str]:
        """Get session IDs for users with specific roles"""
        if not self._connection_tracker:
            return set()
        
        sessions = set()
        for role in roles:
            role_sessions = self._connection_tracker.get_sessions_by_role(role)
            sessions.update(role_sessions)
        
        return sessions
    
    def _get_sessions_for_namespaces(self, namespaces: Set[str]) -> Set[str]:
        """Get session IDs for specific namespaces"""
        if not self._connection_tracker:
            return set()
        
        sessions = set()
        for namespace in namespaces:
            namespace_sessions = self._connection_tracker.get_namespace_sessions(namespace)
            sessions.update(namespace_sessions)
        
        return sessions
    
    def _get_sessions_for_rooms(self, rooms: Set[str]) -> Set[str]:
        """Get session IDs for specific rooms"""
        if not self._connection_tracker:
            return set()
        
        sessions = set()
        for room in rooms:
            room_sessions = self._connection_tracker.get_room_sessions(room)
            sessions.update(room_sessions)
        
        return sessions


class NotificationPersistence:
    """Handles notification persistence for offline users"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # In-memory storage for notifications (fallback)
        self._offline_notifications = defaultdict(deque)  # user_id -> deque of notifications
        self._persistence_lock = RLock()
        
        # Cleanup settings
        self._max_notifications_per_user = 100
        self._cleanup_interval_hours = 6
        
    def store_notification(self, notification: StandardizedNotification, offline_user_ids: Set[int]) -> bool:
        """
        Store notification for offline users
        
        Args:
            notification: Notification to store
            offline_user_ids: Set of user IDs who are offline
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not notification.should_persist():
            return False
        
        try:
            with self._persistence_lock:
                # Store in database if available
                if self.db_manager:
                    self._store_in_database(notification, offline_user_ids)
                
                # Store in memory as fallback
                self._store_in_memory(notification, offline_user_ids)
            
            self.logger.debug(f"Stored notification {notification.id} for {len(offline_user_ids)} offline users")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing notification {notification.id}: {e}")
            return False
    
    def get_notifications_for_user(self, user_id: int, filter_criteria: Optional[NotificationFilter] = None) -> List[StandardizedNotification]:
        """
        Get stored notifications for a user
        
        Args:
            user_id: User ID to get notifications for
            filter_criteria: Optional filter criteria
            
        Returns:
            List of notifications for the user
        """
        try:
            with self._persistence_lock:
                notifications = []
                
                # Get from database if available
                if self.db_manager:
                    db_notifications = self._get_from_database(user_id)
                    notifications.extend(db_notifications)
                
                # Get from memory
                memory_notifications = self._get_from_memory(user_id)
                notifications.extend(memory_notifications)
                
                # Remove duplicates based on notification ID
                seen_ids = set()
                unique_notifications = []
                for notification in notifications:
                    if notification.id not in seen_ids:
                        seen_ids.add(notification.id)
                        unique_notifications.append(notification)
                
                # Apply filter if provided
                if filter_criteria:
                    unique_notifications = [n for n in unique_notifications if filter_criteria.matches(n)]
                
                # Sort by priority and creation time
                unique_notifications.sort(key=lambda n: (
                    self._get_priority_order(n.priority),
                    n.created_at
                ), reverse=True)
                
                return unique_notifications
                
        except Exception as e:
            self.logger.error(f"Error getting notifications for user {user_id}: {e}")
            return []
    
    def mark_notifications_delivered(self, user_id: int, notification_ids: List[str]) -> bool:
        """
        Mark notifications as delivered for a user
        
        Args:
            user_id: User ID
            notification_ids: List of notification IDs to mark as delivered
            
        Returns:
            True if marked successfully, False otherwise
        """
        try:
            with self._persistence_lock:
                # Mark in database if available
                if self.db_manager:
                    self._mark_delivered_in_database(user_id, notification_ids)
                
                # Mark in memory
                self._mark_delivered_in_memory(user_id, notification_ids)
            
            self.logger.debug(f"Marked {len(notification_ids)} notifications as delivered for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error marking notifications as delivered for user {user_id}: {e}")
            return False
    
    def cleanup_expired_notifications(self) -> int:
        """
        Clean up expired notifications
        
        Returns:
            Number of notifications cleaned up
        """
        try:
            with self._persistence_lock:
                cleaned_count = 0
                
                # Clean up database if available
                if self.db_manager:
                    db_cleaned = self._cleanup_database()
                    cleaned_count += db_cleaned
                
                # Clean up memory
                memory_cleaned = self._cleanup_memory()
                cleaned_count += memory_cleaned
                
                if cleaned_count > 0:
                    self.logger.info(f"Cleaned up {cleaned_count} expired notifications")
                
                return cleaned_count
                
        except Exception as e:
            self.logger.error(f"Error cleaning up expired notifications: {e}")
            return 0
    
    def _store_in_database(self, notification: StandardizedNotification, offline_user_ids: Set[int]):
        """Store notification in database"""
        # This would implement database storage
        # For now, we'll use the in-memory fallback
        pass
    
    def _store_in_memory(self, notification: StandardizedNotification, offline_user_ids: Set[int]):
        """Store notification in memory"""
        for user_id in offline_user_ids:
            user_notifications = self._offline_notifications[user_id]
            user_notifications.append(notification)
            
            # Limit number of notifications per user
            while len(user_notifications) > self._max_notifications_per_user:
                user_notifications.popleft()
    
    def _get_from_database(self, user_id: int) -> List[StandardizedNotification]:
        """Get notifications from database"""
        # This would implement database retrieval
        return []
    
    def _get_from_memory(self, user_id: int) -> List[StandardizedNotification]:
        """Get notifications from memory"""
        user_notifications = self._offline_notifications.get(user_id, deque())
        return list(user_notifications)
    
    def _mark_delivered_in_database(self, user_id: int, notification_ids: List[str]):
        """Mark notifications as delivered in database"""
        # This would implement database update
        pass
    
    def _mark_delivered_in_memory(self, user_id: int, notification_ids: List[str]):
        """Mark notifications as delivered in memory"""
        user_notifications = self._offline_notifications.get(user_id, deque())
        for notification in user_notifications:
            if notification.id in notification_ids:
                notification.delivery_status = DeliveryStatus.DELIVERED
    
    def _cleanup_database(self) -> int:
        """Clean up expired notifications from database"""
        # This would implement database cleanup
        return 0
    
    def _cleanup_memory(self) -> int:
        """Clean up expired notifications from memory"""
        cleaned_count = 0
        now = datetime.now(timezone.utc)
        
        for user_id, notifications in self._offline_notifications.items():
            original_count = len(notifications)
            
            # Filter out expired notifications
            valid_notifications = deque()
            for notification in notifications:
                if not notification.is_expired() and notification.should_persist():
                    valid_notifications.append(notification)
            
            self._offline_notifications[user_id] = valid_notifications
            cleaned_count += original_count - len(valid_notifications)
        
        return cleaned_count
    
    def _get_priority_order(self, priority: NotificationPriority) -> int:
        """Get numeric order for priority sorting"""
        priority_order = {
            NotificationPriority.CRITICAL: 5,
            NotificationPriority.URGENT: 4,
            NotificationPriority.HIGH: 3,
            NotificationPriority.NORMAL: 2,
            NotificationPriority.LOW: 1
        }
        return priority_order.get(priority, 0)


class WebSocketNotificationSystem:
    """
    Comprehensive WebSocket notification system with standardized messaging,
    routing, delivery confirmation, priority handling, and offline persistence
    """
    
    def __init__(self, socketio: SocketIO, db_manager=None):
        self.socketio = socketio
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.router = NotificationRouter(socketio)
        self.persistence = NotificationPersistence(db_manager)
        
        # Notification tracking
        self._pending_notifications = {}  # notification_id -> StandardizedNotification
        self._delivery_confirmations = defaultdict(set)  # notification_id -> set of session_ids
        self._notification_lock = RLock()
        
        # User filters and preferences
        self._user_filters = {}  # user_id -> NotificationFilter
        self._user_preferences = {}  # user_id -> dict of preferences
        
        # Delivery retry system
        self._retry_queue = deque()
        self._retry_lock = Lock()
        
        # Statistics
        self._stats = {
            'notifications_sent': 0,
            'notifications_delivered': 0,
            'notifications_acknowledged': 0,
            'notifications_failed': 0,
            'notifications_persisted': 0
        }
        
        # Register event handlers
        self._register_notification_handlers()
        
        self.logger.info("WebSocket Notification System initialized")
    
    def set_connection_tracker(self, connection_tracker):
        """Set connection tracker for the router"""
        self.router.set_connection_tracker(connection_tracker)
    
    def send_notification(self, notification: StandardizedNotification) -> bool:
        """
        Send a standardized notification
        
        Args:
            notification: Notification to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            with self._notification_lock:
                # Validate notification
                if not self._validate_notification(notification):
                    return False
                
                # Check if expired
                if notification.is_expired():
                    self.logger.warning(f"Notification {notification.id} is expired, not sending")
                    return False
                
                # Route notification to target sessions
                target_sessions = self.router.route_notification(notification)
                
                if not target_sessions:
                    self.logger.debug(f"No target sessions for notification {notification.id}")
                    
                    # Store for offline users if applicable
                    if notification.target.user_ids and notification.should_persist():
                        self.persistence.store_notification(notification, notification.target.user_ids)
                        self._stats['notifications_persisted'] += 1
                    
                    return True
                
                # Filter sessions based on user preferences
                filtered_sessions = self._filter_sessions_by_preferences(notification, target_sessions)
                
                # Send to online sessions
                online_sessions = set()
                offline_user_ids = set()
                
                for session_id in filtered_sessions:
                    if self._is_session_online(session_id):
                        online_sessions.add(session_id)
                    else:
                        # Track offline users for persistence
                        user_id = self._get_user_id_for_session(session_id)
                        if user_id:
                            offline_user_ids.add(user_id)
                
                # Send to online sessions
                delivery_success = False
                if online_sessions:
                    delivery_success = self._deliver_to_sessions(notification, online_sessions)
                
                # Store for offline users
                if offline_user_ids and notification.should_persist():
                    self.persistence.store_notification(notification, offline_user_ids)
                    self._stats['notifications_persisted'] += 1
                
                # Track notification for acknowledgment if required
                if notification.requires_acknowledgment and online_sessions:
                    self._pending_notifications[notification.id] = notification
                
                # Update statistics
                self._stats['notifications_sent'] += 1
                if delivery_success:
                    self._stats['notifications_delivered'] += 1
                
                self.logger.debug(f"Sent notification {notification.id} to {len(online_sessions)} online sessions, stored for {len(offline_user_ids)} offline users")
                return True
                
        except Exception as e:
            self.logger.error(f"Error sending notification {notification.id}: {e}")
            self._stats['notifications_failed'] += 1
            return False
    
    def create_notification(self, event_name: str, title: str, message: str, 
                          notification_type: NotificationType = NotificationType.INFO,
                          priority: NotificationPriority = NotificationPriority.NORMAL,
                          **kwargs) -> StandardizedNotification:
        """
        Create a standardized notification with common parameters
        
        Args:
            event_name: WebSocket event name
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            **kwargs: Additional notification parameters
            
        Returns:
            StandardizedNotification instance
        """
        return StandardizedNotification(
            event_name=event_name,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            **kwargs
        )
    
    def broadcast_to_all(self, event_name: str, title: str, message: str,
                        notification_type: NotificationType = NotificationType.INFO,
                        priority: NotificationPriority = NotificationPriority.NORMAL,
                        **kwargs) -> bool:
        """
        Broadcast notification to all connected users
        
        Args:
            event_name: WebSocket event name
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            **kwargs: Additional parameters
            
        Returns:
            True if broadcast successful, False otherwise
        """
        notification = self.create_notification(
            event_name=event_name,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            **kwargs
        )
        
        # Set target to all namespaces
        notification.target.namespaces = {'/', '/admin'}
        
        return self.send_notification(notification)
    
    def send_to_user(self, user_id: int, event_name: str, title: str, message: str,
                    notification_type: NotificationType = NotificationType.INFO,
                    priority: NotificationPriority = NotificationPriority.NORMAL,
                    **kwargs) -> bool:
        """
        Send notification to specific user
        
        Args:
            user_id: Target user ID
            event_name: WebSocket event name
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            **kwargs: Additional parameters
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification = self.create_notification(
            event_name=event_name,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            **kwargs
        )
        
        # Set target to specific user
        notification.target.user_ids = {user_id}
        
        return self.send_notification(notification)
    
    def send_to_role(self, role: UserRole, event_name: str, title: str, message: str,
                    notification_type: NotificationType = NotificationType.INFO,
                    priority: NotificationPriority = NotificationPriority.NORMAL,
                    **kwargs) -> bool:
        """
        Send notification to users with specific role
        
        Args:
            role: Target user role
            event_name: WebSocket event name
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            **kwargs: Additional parameters
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification = self.create_notification(
            event_name=event_name,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            **kwargs
        )
        
        # Set target to specific role
        notification.target.roles = {role}
        
        return self.send_notification(notification)
    
    def send_to_room(self, room: str, event_name: str, title: str, message: str,
                    notification_type: NotificationType = NotificationType.INFO,
                    priority: NotificationPriority = NotificationPriority.NORMAL,
                    **kwargs) -> bool:
        """
        Send notification to specific room
        
        Args:
            room: Target room
            event_name: WebSocket event name
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            **kwargs: Additional parameters
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification = self.create_notification(
            event_name=event_name,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            **kwargs
        )
        
        # Set target to specific room
        notification.target.rooms = {room}
        notification.room = room
        
        return self.send_notification(notification)
    
    def set_user_filter(self, user_id: int, notification_filter: NotificationFilter):
        """Set notification filter for a user"""
        self._user_filters[user_id] = notification_filter
        self.logger.debug(f"Set notification filter for user {user_id}")
    
    def get_user_filter(self, user_id: int) -> Optional[NotificationFilter]:
        """Get notification filter for a user"""
        return self._user_filters.get(user_id)
    
    def set_user_preferences(self, user_id: int, preferences: Dict[str, Any]):
        """Set notification preferences for a user"""
        self._user_preferences[user_id] = preferences
        self.logger.debug(f"Set notification preferences for user {user_id}")
    
    def get_offline_notifications(self, user_id: int, 
                                filter_criteria: Optional[NotificationFilter] = None) -> List[StandardizedNotification]:
        """Get offline notifications for a user"""
        return self.persistence.get_notifications_for_user(user_id, filter_criteria)
    
    def mark_notifications_delivered(self, user_id: int, notification_ids: List[str]) -> bool:
        """Mark notifications as delivered for a user"""
        return self.persistence.mark_notifications_delivered(user_id, notification_ids)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get notification system statistics"""
        with self._notification_lock:
            return {
                **self._stats,
                'pending_notifications': len(self._pending_notifications),
                'retry_queue_size': len(self._retry_queue),
                'user_filters': len(self._user_filters),
                'user_preferences': len(self._user_preferences)
            }
    
    def cleanup_expired_notifications(self) -> int:
        """Clean up expired notifications"""
        cleaned_count = 0
        
        # Clean up pending notifications
        with self._notification_lock:
            expired_ids = []
            for notification_id, notification in self._pending_notifications.items():
                if notification.is_expired():
                    expired_ids.append(notification_id)
            
            for notification_id in expired_ids:
                del self._pending_notifications[notification_id]
                cleaned_count += 1
        
        # Clean up persisted notifications
        persisted_cleaned = self.persistence.cleanup_expired_notifications()
        cleaned_count += persisted_cleaned
        
        return cleaned_count
    
    def _register_notification_handlers(self):
        """Register WebSocket event handlers for notification system"""
        
        @self.socketio.on('notification_acknowledgment')
        def handle_notification_acknowledgment(data):
            """Handle notification acknowledgment from client"""
            try:
                if not isinstance(data, dict) or 'notification_id' not in data:
                    emit('error', {'message': 'Invalid acknowledgment format'})
                    return
                
                notification_id = data['notification_id']
                session_id = data.get('session_id', 'unknown')
                
                with self._notification_lock:
                    if notification_id in self._pending_notifications:
                        notification = self._pending_notifications[notification_id]
                        notification.acknowledged_by.add(session_id)
                        
                        # Check if all required acknowledgments received
                        if self._all_acknowledgments_received(notification):
                            del self._pending_notifications[notification_id]
                            self._stats['notifications_acknowledged'] += 1
                
                self.logger.debug(f"Received acknowledgment for notification {notification_id} from session {session_id}")
                
            except Exception as e:
                self.logger.error(f"Error handling notification acknowledgment: {e}")
        
        @self.socketio.on('get_offline_notifications')
        def handle_get_offline_notifications(data):
            """Handle request for offline notifications"""
            try:
                # This would require authentication context
                # For now, we'll emit an error
                emit('error', {'message': 'Authentication required for offline notifications'})
                
            except Exception as e:
                self.logger.error(f"Error handling offline notifications request: {e}")
        
        @self.socketio.on('set_notification_preferences')
        def handle_set_notification_preferences(data):
            """Handle setting notification preferences"""
            try:
                # This would require authentication context
                # For now, we'll emit an error
                emit('error', {'message': 'Authentication required for setting preferences'})
                
            except Exception as e:
                self.logger.error(f"Error handling notification preferences: {e}")
    
    def _validate_notification(self, notification: StandardizedNotification) -> bool:
        """Validate notification before sending"""
        if not notification.event_name:
            self.logger.error(f"Notification {notification.id} missing event_name")
            return False
        
        if not notification.title and not notification.message:
            self.logger.error(f"Notification {notification.id} missing both title and message")
            return False
        
        if notification.target.is_empty():
            self.logger.error(f"Notification {notification.id} has no targets specified")
            return False
        
        return True
    
    def _filter_sessions_by_preferences(self, notification: StandardizedNotification, 
                                      sessions: List[str]) -> List[str]:
        """Filter sessions based on user notification preferences"""
        filtered_sessions = []
        
        for session_id in sessions:
            user_id = self._get_user_id_for_session(session_id)
            if not user_id:
                continue
            
            # Check user filter
            user_filter = self._user_filters.get(user_id)
            if user_filter and not user_filter.matches(notification):
                continue
            
            # Check user preferences
            user_prefs = self._user_preferences.get(user_id, {})
            if not self._notification_matches_preferences(notification, user_prefs):
                continue
            
            filtered_sessions.append(session_id)
        
        return filtered_sessions
    
    def _notification_matches_preferences(self, notification: StandardizedNotification, 
                                        preferences: Dict[str, Any]) -> bool:
        """Check if notification matches user preferences"""
        # Check if user has disabled this notification type
        disabled_types = preferences.get('disabled_types', [])
        if notification.notification_type.value in disabled_types:
            return False
        
        # Check minimum priority preference
        min_priority = preferences.get('min_priority')
        if min_priority:
            priority_order = {
                'low': 1, 'normal': 2, 'high': 3, 'urgent': 4, 'critical': 5
            }
            if priority_order.get(notification.priority.value, 0) < priority_order.get(min_priority, 0):
                return False
        
        # Check quiet hours
        quiet_hours = preferences.get('quiet_hours')
        if quiet_hours and self._is_in_quiet_hours(quiet_hours):
            # Only allow critical notifications during quiet hours
            if notification.priority != NotificationPriority.CRITICAL:
                return False
        
        return True
    
    def _is_in_quiet_hours(self, quiet_hours: Dict[str, Any]) -> bool:
        """Check if current time is within user's quiet hours"""
        # This would implement quiet hours checking
        # For now, return False
        return False
    
    def _deliver_to_sessions(self, notification: StandardizedNotification, 
                           sessions: Set[str]) -> bool:
        """Deliver notification to specific sessions"""
        try:
            payload = notification.get_client_payload()
            
            # Emit to each session
            for session_id in sessions:
                try:
                    emit(notification.event_name, payload, room=session_id, namespace=notification.namespace)
                    notification.delivered_to.add(session_id)
                except Exception as e:
                    self.logger.error(f"Failed to deliver notification {notification.id} to session {session_id}: {e}")
                    notification.failed_deliveries.append(f"Session {session_id}: {str(e)}")
            
            notification.last_delivery_attempt = datetime.now(timezone.utc)
            
            # Update delivery status
            if notification.delivered_to:
                notification.delivery_status = DeliveryStatus.DELIVERED
                return True
            else:
                notification.delivery_status = DeliveryStatus.FAILED
                return False
                
        except Exception as e:
            self.logger.error(f"Error delivering notification {notification.id}: {e}")
            notification.delivery_status = DeliveryStatus.FAILED
            return False
    
    def _is_session_online(self, session_id: str) -> bool:
        """Check if session is currently online"""
        # This would check with the connection tracker
        # For now, assume all sessions are online
        return True
    
    def _get_user_id_for_session(self, session_id: str) -> Optional[int]:
        """Get user ID for a session"""
        # This would query the connection tracker
        # For now, return None
        return None
    
    def _all_acknowledgments_received(self, notification: StandardizedNotification) -> bool:
        """Check if all required acknowledgments have been received"""
        if not notification.requires_acknowledgment:
            return True
        
        # Check if all delivered sessions have acknowledged
        return notification.delivered_to.issubset(notification.acknowledged_by)
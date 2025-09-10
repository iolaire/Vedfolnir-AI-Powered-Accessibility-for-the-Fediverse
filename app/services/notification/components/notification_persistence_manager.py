# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Persistence Manager

This module manages notification storage, queuing, and replay for offline users.
It provides database storage for notification persistence, offline user message queuing,
delivery confirmation tracking, automatic cleanup of old notifications, and message
replay for reconnecting users.
"""

import logging
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import and_, or_, desc, func
from sqlalchemy.exc import SQLAlchemyError

from database import DatabaseManager
from unified_notification_manager import NotificationMessage
from models import NotificationStorage, NotificationType, NotificationPriority, NotificationCategory

logger = logging.getLogger(__name__)


class QueueStatus(Enum):
    """Offline queue status"""
    ACTIVE = "active"
    PAUSED = "paused"
    FULL = "full"
    ERROR = "error"


@dataclass
class OfflineQueueInfo:
    """Information about offline message queue"""
    user_id: int
    queue_size: int
    oldest_message_timestamp: Optional[datetime]
    newest_message_timestamp: Optional[datetime]
    status: QueueStatus
    last_delivery_attempt: Optional[datetime]
    total_messages_queued: int
    total_messages_delivered: int


@dataclass
class DeliveryTrackingInfo:
    """Delivery tracking information"""
    message_id: str
    user_id: int
    queued_at: datetime
    delivered_at: Optional[datetime]
    delivery_attempts: int
    last_attempt_at: Optional[datetime]
    delivery_confirmed: bool
    error_message: Optional[str]


class NotificationPersistenceManager:
    """
    Manages notification storage, queuing, and replay for offline users
    
    Provides database storage for notification persistence, offline user message queuing,
    delivery confirmation tracking, automatic cleanup of old notifications, and message
    replay for reconnecting users.
    """
    
    def __init__(self, db_manager: DatabaseManager, max_offline_messages: int = 100,
                 retention_days: int = 30, cleanup_interval_hours: int = 24):
        """
        Initialize notification persistence manager
        
        Args:
            db_manager: Database manager instance
            max_offline_messages: Maximum offline messages per user
            retention_days: Days to retain messages in database
            cleanup_interval_hours: Hours between automatic cleanup runs
        """
        self.db_manager = db_manager
        self.max_offline_messages = max_offline_messages
        self.retention_days = retention_days
        self.cleanup_interval_hours = cleanup_interval_hours
        
        # In-memory offline queues for fast access
        self._offline_queues = defaultdict(deque)  # user_id -> deque of message_ids
        self._queue_info = {}  # user_id -> OfflineQueueInfo
        
        # Delivery tracking
        self._delivery_tracking = {}  # message_id -> DeliveryTrackingInfo
        self._pending_deliveries = defaultdict(set)  # user_id -> set of message_ids
        
        # Statistics
        self._stats = {
            'messages_stored': 0,
            'messages_queued': 0,
            'messages_delivered': 0,
            'messages_expired': 0,
            'cleanup_runs': 0,
            'storage_errors': 0
        }
        
        # Last cleanup time
        self._last_cleanup = datetime.now(timezone.utc)
        
        logger.info("Notification Persistence Manager initialized")
    
    def store_notification(self, notification: NotificationMessage) -> str:
        """
        Store notification in database
        
        Args:
            notification: Notification message to store
            
        Returns:
            Notification ID if stored successfully, empty string otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                # Create database record
                db_notification = NotificationStorage(
                    id=notification.id,
                    user_id=notification.user_id,
                    type=notification.type,
                    priority=notification.priority,
                    category=notification.category,
                    title=notification.title,
                    message=notification.message,
                    data=json.dumps(notification.data) if notification.data else None,
                    timestamp=notification.timestamp or datetime.now(timezone.utc),
                    expires_at=notification.expires_at,
                    requires_action=notification.requires_action,
                    action_url=notification.action_url,
                    action_text=notification.action_text,
                    delivered=notification.delivered,
                    read=notification.read
                )
                
                session.add(db_notification)
                session.commit()
                
                self._stats['messages_stored'] += 1
                logger.debug(f"Stored notification {notification.id} in database")
                
                return notification.id
                
        except SQLAlchemyError as e:
            logger.error(f"Database error storing notification: {e}")
            self._stats['storage_errors'] += 1
            return ""
        except Exception as e:
            logger.error(f"Failed to store notification: {e}")
            self._stats['storage_errors'] += 1
            return ""
    
    def queue_for_offline_user(self, user_id: int, notification: NotificationMessage) -> None:
        """
        Queue notification for offline user
        
        Args:
            user_id: User ID to queue message for
            notification: Notification message to queue
        """
        try:
            # Store in database first
            notification_id = self.store_notification(notification)
            if not notification_id:
                logger.error(f"Failed to store notification for queuing: {notification.id}")
                return
            
            # Add to offline queue
            queue = self._offline_queues[user_id]
            
            # Check queue size limit
            if len(queue) >= self.max_offline_messages:
                # Remove oldest message
                oldest_id = queue.popleft()
                self._remove_from_tracking(oldest_id)
                logger.debug(f"Removed oldest message {oldest_id} from queue for user {user_id}")
            
            # Add new message
            queue.append(notification_id)
            self._pending_deliveries[user_id].add(notification_id)
            
            # Update queue info
            self._update_queue_info(user_id)
            
            # Create delivery tracking
            self._delivery_tracking[notification_id] = DeliveryTrackingInfo(
                message_id=notification_id,
                user_id=user_id,
                queued_at=datetime.now(timezone.utc),
                delivered_at=None,
                delivery_attempts=0,
                last_attempt_at=None,
                delivery_confirmed=False,
                error_message=None
            )
            
            self._stats['messages_queued'] += 1
            logger.debug(f"Queued notification {notification_id} for offline user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to queue notification for offline user: {e}")
    
    def get_pending_notifications(self, user_id: int) -> List[NotificationMessage]:
        """
        Get pending notifications for user
        
        Args:
            user_id: User ID to get notifications for
            
        Returns:
            List of pending notification messages
        """
        try:
            # Get message IDs from offline queue
            queue = self._offline_queues.get(user_id, deque())
            message_ids = list(queue)
            
            if not message_ids:
                return []
            
            # Retrieve messages from database
            with self.db_manager.get_session() as session:
                notifications = session.query(NotificationStorage)\
                    .filter(NotificationStorage.id.in_(message_ids))\
                    .filter_by(delivered=False)\
                    .order_by(NotificationStorage.timestamp)\
                    .all()
                
                return [notif.to_notification_message() for notif in notifications]
                
        except Exception as e:
            logger.error(f"Failed to get pending notifications for user {user_id}: {e}")
            return []
    
    def mark_as_delivered(self, notification_id: str) -> bool:
        """
        Mark notification as delivered
        
        Args:
            notification_id: Notification ID to mark as delivered
            
        Returns:
            True if marked successfully, False otherwise
        """
        try:
            # Update database
            with self.db_manager.get_session() as session:
                notification = session.query(NotificationStorage)\
                    .filter_by(id=notification_id)\
                    .first()
                
                if not notification:
                    logger.warning(f"Notification {notification_id} not found for delivery marking")
                    return False
                
                notification.delivered = True
                notification.updated_at = datetime.utcnow()
                session.commit()
                
                user_id = notification.user_id
            
            # Update tracking
            tracking_info = self._delivery_tracking.get(notification_id)
            if tracking_info:
                tracking_info.delivered_at = datetime.now(timezone.utc)
                tracking_info.delivery_confirmed = True
            
            # Remove from offline queue
            if user_id:
                queue = self._offline_queues.get(user_id, deque())
                if notification_id in queue:
                    queue.remove(notification_id)
                
                self._pending_deliveries[user_id].discard(notification_id)
                self._update_queue_info(user_id)
            
            self._stats['messages_delivered'] += 1
            logger.debug(f"Marked notification {notification_id} as delivered")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark notification as delivered: {e}")
            return False
    
    def cleanup_old_notifications(self, retention_days: Optional[int] = None) -> int:
        """
        Clean up old notifications from database and memory
        
        Args:
            retention_days: Days to retain (uses default if None)
            
        Returns:
            Number of notifications cleaned up
        """
        try:
            cleanup_count = 0
            retention_period = retention_days or self.retention_days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_period)
            
            with self.db_manager.get_session() as session:
                # Clean up old notifications
                old_notifications = session.query(NotificationStorage)\
                    .filter(NotificationStorage.created_at < cutoff_date)\
                    .all()
                
                notification_ids = [notif.id for notif in old_notifications]
                
                # Remove from database
                for notification in old_notifications:
                    session.delete(notification)
                    cleanup_count += 1
                
                session.commit()
                
                # Clean up from memory structures
                for notification_id in notification_ids:
                    self._remove_from_tracking(notification_id)
            
            # Clean up expired notifications
            current_time = datetime.now(timezone.utc)
            with self.db_manager.get_session() as session:
                expired_notifications = session.query(NotificationStorage)\
                    .filter(NotificationStorage.expires_at < current_time)\
                    .all()
                
                for notification in expired_notifications:
                    session.delete(notification)
                    self._remove_from_tracking(notification.id)
                    cleanup_count += 1
                
                session.commit()
            
            # Update statistics
            self._stats['messages_expired'] += cleanup_count
            self._stats['cleanup_runs'] += 1
            self._last_cleanup = datetime.now(timezone.utc)
            
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} old/expired notifications")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old notifications: {e}")
            return 0
    
    def get_notification_by_id(self, notification_id: str) -> Optional[NotificationMessage]:
        """
        Get notification by ID from database
        
        Args:
            notification_id: Notification ID to retrieve
            
        Returns:
            Notification message or None if not found
        """
        try:
            with self.db_manager.get_session() as session:
                notification = session.query(NotificationStorage)\
                    .filter_by(id=notification_id)\
                    .first()
                
                if notification:
                    return notification.to_notification_message()
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get notification by ID: {e}")
            return None
    
    def get_user_notifications(self, user_id: int, limit: int = 50, 
                             include_read: bool = True) -> List[NotificationMessage]:
        """
        Get notifications for a specific user
        
        Args:
            user_id: User ID to get notifications for
            limit: Maximum number of notifications to return
            include_read: Whether to include read notifications
            
        Returns:
            List of notification messages
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(NotificationStorage)\
                    .filter_by(user_id=user_id)
                
                if not include_read:
                    query = query.filter_by(read=False)
                
                notifications = query.order_by(desc(NotificationStorage.timestamp))\
                    .limit(limit)\
                    .all()
                
                return [notif.to_notification_message() for notif in notifications]
                
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return []
    
    def mark_notification_as_read(self, notification_id: str, user_id: int) -> bool:
        """
        Mark notification as read by user
        
        Args:
            notification_id: Notification ID to mark as read
            user_id: User ID who read the notification
            
        Returns:
            True if marked successfully, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                notification = session.query(NotificationStorage)\
                    .filter_by(id=notification_id, user_id=user_id)\
                    .first()
                
                if notification:
                    notification.read = True
                    notification.updated_at = datetime.utcnow()
                    session.commit()
                    
                    logger.debug(f"Marked notification {notification_id} as read for user {user_id}")
                    return True
                else:
                    logger.warning(f"Notification {notification_id} not found for user {user_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return False
    
    def get_queue_info(self, user_id: int) -> Optional[OfflineQueueInfo]:
        """
        Get offline queue information for user
        
        Args:
            user_id: User ID to get queue info for
            
        Returns:
            Queue information or None if no queue exists
        """
        try:
            return self._queue_info.get(user_id)
            
        except Exception as e:
            logger.error(f"Failed to get queue info: {e}")
            return None
    
    def get_delivery_stats(self) -> Dict[str, Any]:
        """
        Get delivery statistics
        
        Returns:
            Dictionary containing delivery statistics
        """
        try:
            # Count delivery tracking by status
            delivered_count = sum(1 for info in self._delivery_tracking.values() 
                                if info.delivery_confirmed)
            pending_count = sum(1 for info in self._delivery_tracking.values() 
                              if not info.delivery_confirmed)
            
            # Count queue statistics
            total_queued = sum(len(queue) for queue in self._offline_queues.values())
            active_queues = len([q for q in self._queue_info.values() 
                               if q.status == QueueStatus.ACTIVE])
            
            # Database statistics
            with self.db_manager.get_session() as session:
                total_in_db = session.query(NotificationStorage).count()
                undelivered_in_db = session.query(NotificationStorage)\
                    .filter_by(delivered=False).count()
                unread_in_db = session.query(NotificationStorage)\
                    .filter_by(read=False).count()
            
            return {
                'persistence_stats': self._stats,
                'delivery_tracking': {
                    'total_tracked': len(self._delivery_tracking),
                    'delivered': delivered_count,
                    'pending': pending_count
                },
                'offline_queues': {
                    'total_users': len(self._offline_queues),
                    'active_queues': active_queues,
                    'total_messages_queued': total_queued,
                    'max_messages_per_user': self.max_offline_messages
                },
                'database_stats': {
                    'total_notifications': total_in_db,
                    'undelivered': undelivered_in_db,
                    'unread': unread_in_db
                },
                'configuration': {
                    'retention_days': self.retention_days,
                    'cleanup_interval_hours': self.cleanup_interval_hours,
                    'last_cleanup': self._last_cleanup.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get delivery stats: {e}")
            return {'error': str(e)}
    
    def replay_messages_for_user(self, user_id: int) -> List[NotificationMessage]:
        """
        Get messages to replay for reconnecting user
        
        Args:
            user_id: User ID to get replay messages for
            
        Returns:
            List of messages to replay
        """
        try:
            # Get pending messages from queue
            pending_messages = self.get_pending_notifications(user_id)
            
            # Update delivery attempts for tracking
            for message in pending_messages:
                tracking_info = self._delivery_tracking.get(message.id)
                if tracking_info:
                    tracking_info.delivery_attempts += 1
                    tracking_info.last_attempt_at = datetime.now(timezone.utc)
            
            logger.debug(f"Prepared {len(pending_messages)} messages for replay to user {user_id}")
            return pending_messages
            
        except Exception as e:
            logger.error(f"Failed to get replay messages for user {user_id}: {e}")
            return []
    
    def pause_queue(self, user_id: int) -> bool:
        """
        Pause offline queue for user
        
        Args:
            user_id: User ID to pause queue for
            
        Returns:
            True if paused successfully, False otherwise
        """
        try:
            queue_info = self._queue_info.get(user_id)
            if queue_info:
                queue_info.status = QueueStatus.PAUSED
                logger.debug(f"Paused offline queue for user {user_id}")
                return True
            else:
                logger.warning(f"No queue found for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to pause queue for user {user_id}: {e}")
            return False
    
    def resume_queue(self, user_id: int) -> bool:
        """
        Resume offline queue for user
        
        Args:
            user_id: User ID to resume queue for
            
        Returns:
            True if resumed successfully, False otherwise
        """
        try:
            queue_info = self._queue_info.get(user_id)
            if queue_info:
                queue_info.status = QueueStatus.ACTIVE
                logger.debug(f"Resumed offline queue for user {user_id}")
                return True
            else:
                logger.warning(f"No queue found for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to resume queue for user {user_id}: {e}")
            return False
    
    def clear_user_queue(self, user_id: int) -> int:
        """
        Clear all messages from user's offline queue
        
        Args:
            user_id: User ID to clear queue for
            
        Returns:
            Number of messages cleared
        """
        try:
            queue = self._offline_queues.get(user_id, deque())
            message_ids = list(queue)
            cleared_count = len(message_ids)
            
            # Clear from memory
            queue.clear()
            self._pending_deliveries[user_id].clear()
            
            # Remove tracking
            for message_id in message_ids:
                self._remove_from_tracking(message_id)
            
            # Update queue info
            self._update_queue_info(user_id)
            
            logger.info(f"Cleared {cleared_count} messages from queue for user {user_id}")
            return cleared_count
            
        except Exception as e:
            logger.error(f"Failed to clear queue for user {user_id}: {e}")
            return 0
    
    def _update_queue_info(self, user_id: int) -> None:
        """
        Update queue information for user
        
        Args:
            user_id: User ID to update queue info for
        """
        try:
            queue = self._offline_queues.get(user_id, deque())
            
            if not queue:
                # Remove queue info if queue is empty
                self._queue_info.pop(user_id, None)
                return
            
            # Get timestamps from tracking info
            oldest_timestamp = None
            newest_timestamp = None
            
            for message_id in queue:
                tracking_info = self._delivery_tracking.get(message_id)
                if tracking_info:
                    if oldest_timestamp is None or tracking_info.queued_at < oldest_timestamp:
                        oldest_timestamp = tracking_info.queued_at
                    if newest_timestamp is None or tracking_info.queued_at > newest_timestamp:
                        newest_timestamp = tracking_info.queued_at
            
            # Determine queue status
            status = QueueStatus.ACTIVE
            if len(queue) >= self.max_offline_messages:
                status = QueueStatus.FULL
            
            # Get delivery statistics
            user_tracking = [info for info in self._delivery_tracking.values() 
                           if info.user_id == user_id]
            total_queued = len(user_tracking)
            total_delivered = sum(1 for info in user_tracking if info.delivery_confirmed)
            
            # Get last delivery attempt
            last_attempt = None
            for info in user_tracking:
                if info.last_attempt_at:
                    if last_attempt is None or info.last_attempt_at > last_attempt:
                        last_attempt = info.last_attempt_at
            
            # Update queue info
            self._queue_info[user_id] = OfflineQueueInfo(
                user_id=user_id,
                queue_size=len(queue),
                oldest_message_timestamp=oldest_timestamp,
                newest_message_timestamp=newest_timestamp,
                status=status,
                last_delivery_attempt=last_attempt,
                total_messages_queued=total_queued,
                total_messages_delivered=total_delivered
            )
            
        except Exception as e:
            logger.error(f"Failed to update queue info for user {user_id}: {e}")
    
    def _remove_from_tracking(self, notification_id: str) -> None:
        """
        Remove notification from tracking structures
        
        Args:
            notification_id: Notification ID to remove
        """
        try:
            # Remove from delivery tracking
            tracking_info = self._delivery_tracking.pop(notification_id, None)
            
            # Remove from pending deliveries
            if tracking_info:
                self._pending_deliveries[tracking_info.user_id].discard(notification_id)
            
        except Exception as e:
            logger.error(f"Failed to remove tracking for notification {notification_id}: {e}")
    
    def should_run_cleanup(self) -> bool:
        """
        Check if automatic cleanup should run
        
        Returns:
            True if cleanup should run, False otherwise
        """
        try:
            time_since_cleanup = datetime.now(timezone.utc) - self._last_cleanup
            return time_since_cleanup.total_seconds() >= (self.cleanup_interval_hours * 3600)
            
        except Exception as e:
            logger.error(f"Failed to check cleanup schedule: {e}")
            return False
    
    def get_notification_counts_by_category(self, user_id: Optional[int] = None) -> Dict[str, int]:
        """
        Get notification counts by category
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            Dictionary mapping categories to counts
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(
                    NotificationStorage.category,
                    func.count(NotificationStorage.id).label('count')
                )
                
                if user_id:
                    query = query.filter_by(user_id=user_id)
                
                results = query.group_by(NotificationStorage.category).all()
                
                return {category.value: count for category, count in results}
                
        except Exception as e:
            logger.error(f"Failed to get notification counts by category: {e}")
            return {}
    
    def get_unread_count(self, user_id: int) -> int:
        """
        Get count of unread notifications for user
        
        Args:
            user_id: User ID to get unread count for
            
        Returns:
            Number of unread notifications
        """
        try:
            with self.db_manager.get_session() as session:
                count = session.query(NotificationStorage)\
                    .filter_by(user_id=user_id, read=False)\
                    .count()
                
                return count
                
        except Exception as e:
            logger.error(f"Failed to get unread count for user {user_id}: {e}")
            return 0
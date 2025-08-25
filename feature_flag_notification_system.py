# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH the SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Feature Flag Change Notification System

Provides real-time notification system for feature flag changes with
service subscription management and change propagation within 30 seconds.
"""

import logging
import threading
import time
import asyncio
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import queue
import concurrent.futures

from feature_flag_service import FeatureFlagService

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(Enum):
    """Notification delivery channels"""
    CALLBACK = "callback"
    WEBHOOK = "webhook"
    EMAIL = "email"
    LOG = "log"
    QUEUE = "queue"


@dataclass
class FeatureFlagChangeNotification:
    """Feature flag change notification"""
    notification_id: str
    feature_key: str
    old_value: bool
    new_value: bool
    timestamp: datetime
    priority: NotificationPriority = NotificationPriority.NORMAL
    source: str = "system"
    admin_user_id: Optional[int] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary"""
        return {
            'notification_id': self.notification_id,
            'feature_key': self.feature_key,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority.value,
            'source': self.source,
            'admin_user_id': self.admin_user_id,
            'reason': self.reason,
            'metadata': self.metadata
        }


@dataclass
class ServiceSubscription:
    """Service subscription to feature flag changes"""
    subscription_id: str
    service_name: str
    feature_keys: Set[str]  # Features this service is interested in
    callback: Callable[[FeatureFlagChangeNotification], None]
    channels: List[NotificationChannel]
    priority_filter: Optional[NotificationPriority] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_notified: Optional[datetime] = None
    notification_count: int = 0
    is_active: bool = True
    
    def matches_notification(self, notification: FeatureFlagChangeNotification) -> bool:
        """Check if this subscription matches the notification"""
        if not self.is_active:
            return False
        
        # Check feature key match
        if '*' not in self.feature_keys and notification.feature_key not in self.feature_keys:
            return False
        
        # Check priority filter
        if self.priority_filter and notification.priority != self.priority_filter:
            return False
        
        return True


@dataclass
class NotificationMetrics:
    """Notification system metrics"""
    total_notifications: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    average_delivery_time_ms: float = 0.0
    subscriptions_count: int = 0
    active_subscriptions: int = 0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FeatureFlagNotificationSystem:
    """
    Real-time notification system for feature flag changes
    
    Features:
    - Service subscription management
    - Multiple notification channels
    - Priority-based filtering
    - Change propagation within 30 seconds
    - Usage metrics collection
    - Delivery confirmation and retry
    """
    
    def __init__(self, feature_service: FeatureFlagService,
                 max_workers: int = 4,
                 delivery_timeout: int = 30,
                 retry_attempts: int = 3):
        """
        Initialize notification system
        
        Args:
            feature_service: FeatureFlagService instance
            max_workers: Maximum worker threads for notifications
            delivery_timeout: Maximum delivery time in seconds
            retry_attempts: Number of retry attempts for failed deliveries
        """
        self.feature_service = feature_service
        self.max_workers = max_workers
        self.delivery_timeout = delivery_timeout
        self.retry_attempts = retry_attempts
        
        # Subscription management
        self._subscriptions: Dict[str, ServiceSubscription] = {}
        self._subscriptions_by_feature: Dict[str, Set[str]] = {}
        self._subscriptions_lock = threading.RLock()
        
        # Notification queue and processing
        self._notification_queue = queue.Queue(maxsize=1000)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._processing_thread = None
        self._shutdown_event = threading.Event()
        
        # Metrics and monitoring
        self._metrics = NotificationMetrics()
        self._metrics_lock = threading.RLock()
        
        # Delivery tracking
        self._pending_deliveries: Dict[str, datetime] = {}
        self._delivery_lock = threading.RLock()
        
        # Subscribe to feature flag changes
        self._setup_feature_flag_subscription()
        
        # Start notification processing
        self._start_processing()
    
    def subscribe_service(self, 
                         service_name: str,
                         feature_keys: List[str],
                         callback: Callable[[FeatureFlagChangeNotification], None],
                         channels: List[NotificationChannel] = None,
                         priority_filter: NotificationPriority = None) -> str:
        """
        Subscribe a service to feature flag changes
        
        Args:
            service_name: Name of the subscribing service
            feature_keys: List of feature keys to watch (use '*' for all)
            callback: Callback function for notifications
            channels: Notification channels to use
            priority_filter: Optional priority filter
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        
        if channels is None:
            channels = [NotificationChannel.CALLBACK]
        
        subscription = ServiceSubscription(
            subscription_id=subscription_id,
            service_name=service_name,
            feature_keys=set(feature_keys),
            callback=callback,
            channels=channels,
            priority_filter=priority_filter
        )
        
        with self._subscriptions_lock:
            self._subscriptions[subscription_id] = subscription
            
            # Index by feature keys
            for feature_key in feature_keys:
                if feature_key not in self._subscriptions_by_feature:
                    self._subscriptions_by_feature[feature_key] = set()
                self._subscriptions_by_feature[feature_key].add(subscription_id)
            
            # Update metrics
            with self._metrics_lock:
                self._metrics.subscriptions_count = len(self._subscriptions)
                self._metrics.active_subscriptions = len([s for s in self._subscriptions.values() if s.is_active])
        
        logger.info(f"Service '{service_name}' subscribed to feature flags {feature_keys} with subscription {subscription_id}")
        return subscription_id
    
    def unsubscribe_service(self, subscription_id: str) -> bool:
        """
        Unsubscribe a service from feature flag changes
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed
        """
        with self._subscriptions_lock:
            subscription = self._subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            # Remove from main storage
            del self._subscriptions[subscription_id]
            
            # Remove from feature key indexes
            for feature_key in subscription.feature_keys:
                if feature_key in self._subscriptions_by_feature:
                    self._subscriptions_by_feature[feature_key].discard(subscription_id)
                    if not self._subscriptions_by_feature[feature_key]:
                        del self._subscriptions_by_feature[feature_key]
            
            # Update metrics
            with self._metrics_lock:
                self._metrics.subscriptions_count = len(self._subscriptions)
                self._metrics.active_subscriptions = len([s for s in self._subscriptions.values() if s.is_active])
        
        logger.info(f"Unsubscribed service subscription {subscription_id}")
        return True
    
    def pause_subscription(self, subscription_id: str) -> bool:
        """
        Pause a subscription temporarily
        
        Args:
            subscription_id: Subscription ID to pause
            
        Returns:
            True if subscription was found and paused
        """
        with self._subscriptions_lock:
            subscription = self._subscriptions.get(subscription_id)
            if subscription:
                subscription.is_active = False
                logger.info(f"Paused subscription {subscription_id}")
                return True
            return False
    
    def resume_subscription(self, subscription_id: str) -> bool:
        """
        Resume a paused subscription
        
        Args:
            subscription_id: Subscription ID to resume
            
        Returns:
            True if subscription was found and resumed
        """
        with self._subscriptions_lock:
            subscription = self._subscriptions.get(subscription_id)
            if subscription:
                subscription.is_active = True
                logger.info(f"Resumed subscription {subscription_id}")
                return True
            return False
    
    def notify_feature_change(self, 
                             feature_key: str,
                             old_value: bool,
                             new_value: bool,
                             priority: NotificationPriority = NotificationPriority.NORMAL,
                             source: str = "system",
                             admin_user_id: Optional[int] = None,
                             reason: Optional[str] = None) -> str:
        """
        Notify subscribers of a feature flag change
        
        Args:
            feature_key: Feature flag key that changed
            old_value: Previous value
            new_value: New value
            priority: Notification priority
            source: Source of the change
            admin_user_id: Optional admin user ID
            reason: Optional reason for the change
            
        Returns:
            Notification ID
        """
        notification = FeatureFlagChangeNotification(
            notification_id=str(uuid.uuid4()),
            feature_key=feature_key,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.now(timezone.utc),
            priority=priority,
            source=source,
            admin_user_id=admin_user_id,
            reason=reason
        )
        
        try:
            self._notification_queue.put_nowait(notification)
            
            with self._metrics_lock:
                self._metrics.total_notifications += 1
            
            logger.info(f"Queued notification {notification.notification_id} for feature {feature_key}")
            return notification.notification_id
            
        except queue.Full:
            logger.error("Notification queue is full, dropping notification")
            return ""
    
    def get_subscription_info(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a subscription
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            Dictionary with subscription details or None
        """
        with self._subscriptions_lock:
            subscription = self._subscriptions.get(subscription_id)
            if not subscription:
                return None
            
            return {
                'subscription_id': subscription.subscription_id,
                'service_name': subscription.service_name,
                'feature_keys': list(subscription.feature_keys),
                'channels': [channel.value for channel in subscription.channels],
                'priority_filter': subscription.priority_filter.value if subscription.priority_filter else None,
                'created_at': subscription.created_at,
                'last_notified': subscription.last_notified,
                'notification_count': subscription.notification_count,
                'is_active': subscription.is_active
            }
    
    def list_subscriptions(self, service_name: str = None) -> List[Dict[str, Any]]:
        """
        List all subscriptions, optionally filtered by service name
        
        Args:
            service_name: Optional service name filter
            
        Returns:
            List of subscription information dictionaries
        """
        subscriptions = []
        
        with self._subscriptions_lock:
            for subscription in self._subscriptions.values():
                if service_name is None or subscription.service_name == service_name:
                    subscriptions.append({
                        'subscription_id': subscription.subscription_id,
                        'service_name': subscription.service_name,
                        'feature_keys': list(subscription.feature_keys),
                        'channels': [channel.value for channel in subscription.channels],
                        'priority_filter': subscription.priority_filter.value if subscription.priority_filter else None,
                        'created_at': subscription.created_at,
                        'last_notified': subscription.last_notified,
                        'notification_count': subscription.notification_count,
                        'is_active': subscription.is_active
                    })
        
        return subscriptions
    
    def get_metrics(self) -> NotificationMetrics:
        """
        Get notification system metrics
        
        Returns:
            NotificationMetrics object
        """
        with self._metrics_lock:
            return NotificationMetrics(
                total_notifications=self._metrics.total_notifications,
                successful_deliveries=self._metrics.successful_deliveries,
                failed_deliveries=self._metrics.failed_deliveries,
                average_delivery_time_ms=self._metrics.average_delivery_time_ms,
                subscriptions_count=self._metrics.subscriptions_count,
                active_subscriptions=self._metrics.active_subscriptions,
                last_reset=self._metrics.last_reset
            )
    
    def reset_metrics(self) -> None:
        """Reset notification metrics"""
        with self._metrics_lock:
            self._metrics = NotificationMetrics()
        
        logger.info("Notification system metrics reset")
    
    def get_pending_deliveries(self) -> Dict[str, datetime]:
        """
        Get pending delivery information
        
        Returns:
            Dictionary mapping notification IDs to delivery start times
        """
        with self._delivery_lock:
            return self._pending_deliveries.copy()
    
    def shutdown(self, timeout: float = 5.0) -> bool:
        """
        Shutdown notification system
        
        Args:
            timeout: Timeout in seconds to wait for shutdown
            
        Returns:
            True if shutdown completed successfully
        """
        logger.info("Shutting down feature flag notification system")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for processing thread to finish
        if self._processing_thread and self._processing_thread.is_alive():
            self._processing_thread.join(timeout=timeout)
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        # Clear subscriptions
        with self._subscriptions_lock:
            self._subscriptions.clear()
            self._subscriptions_by_feature.clear()
        
        logger.info("Feature flag notification system shutdown complete")
        return True
    
    def _setup_feature_flag_subscription(self):
        """Setup subscription to feature flag service changes"""
        try:
            # Subscribe to all feature flag changes
            self.feature_service.subscribe_to_flag_changes(
                '*',  # All features
                self._handle_feature_flag_change
            )
            
            logger.info("Subscribed to feature flag service changes")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to feature flag changes: {e}")
    
    def _handle_feature_flag_change(self, feature_key: str, old_value: bool, new_value: bool):
        """
        Handle feature flag changes from the feature service
        
        Args:
            feature_key: Feature flag key that changed
            old_value: Previous value
            new_value: New value
        """
        try:
            # Determine priority based on feature importance
            priority = NotificationPriority.NORMAL
            if feature_key in ['enable_batch_processing', 'maintenance_mode']:
                priority = NotificationPriority.HIGH
            elif feature_key.startswith('enable_'):
                priority = NotificationPriority.NORMAL
            else:
                priority = NotificationPriority.LOW
            
            # Create and queue notification
            self.notify_feature_change(
                feature_key=feature_key,
                old_value=old_value,
                new_value=new_value,
                priority=priority,
                source="feature_service"
            )
            
        except Exception as e:
            logger.error(f"Error handling feature flag change for {feature_key}: {e}")
    
    def _start_processing(self):
        """Start the notification processing thread"""
        self._processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self._processing_thread.start()
        logger.info("Started notification processing thread")
    
    def _processing_loop(self):
        """Main notification processing loop"""
        logger.info("Notification processing loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Get notification from queue with timeout
                try:
                    notification = self._notification_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process notification
                self._process_notification(notification)
                
                # Mark task as done
                self._notification_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in notification processing loop: {e}")
        
        logger.info("Notification processing loop stopped")
    
    def _process_notification(self, notification: FeatureFlagChangeNotification):
        """
        Process a single notification by delivering to subscribers
        
        Args:
            notification: Notification to process
        """
        try:
            # Find matching subscribers
            subscribers = self._find_matching_subscribers(notification)
            
            if not subscribers:
                logger.debug(f"No subscribers for feature {notification.feature_key}")
                return
            
            # Track delivery start time
            with self._delivery_lock:
                self._pending_deliveries[notification.notification_id] = datetime.now(timezone.utc)
            
            # Deliver to subscribers
            delivery_start = time.time()
            successful_deliveries = 0
            failed_deliveries = 0
            
            for subscription_id in subscribers:
                try:
                    success = self._deliver_notification(subscription_id, notification)
                    if success:
                        successful_deliveries += 1
                    else:
                        failed_deliveries += 1
                except Exception as e:
                    logger.error(f"Error delivering notification to {subscription_id}: {e}")
                    failed_deliveries += 1
            
            # Update metrics
            delivery_time = (time.time() - delivery_start) * 1000  # Convert to milliseconds
            
            with self._metrics_lock:
                self._metrics.successful_deliveries += successful_deliveries
                self._metrics.failed_deliveries += failed_deliveries
                
                # Update average delivery time
                total_deliveries = self._metrics.successful_deliveries + self._metrics.failed_deliveries
                if total_deliveries > 0:
                    self._metrics.average_delivery_time_ms = (
                        (self._metrics.average_delivery_time_ms * (total_deliveries - successful_deliveries - failed_deliveries) + 
                         delivery_time) / total_deliveries
                    )
            
            # Remove from pending deliveries
            with self._delivery_lock:
                self._pending_deliveries.pop(notification.notification_id, None)
            
            logger.info(f"Processed notification {notification.notification_id}: "
                       f"{successful_deliveries} successful, {failed_deliveries} failed")
            
        except Exception as e:
            logger.error(f"Error processing notification {notification.notification_id}: {e}")
    
    def _find_matching_subscribers(self, notification: FeatureFlagChangeNotification) -> List[str]:
        """
        Find subscribers that match the notification
        
        Args:
            notification: Notification to match
            
        Returns:
            List of subscription IDs
        """
        matching_subscribers = []
        
        with self._subscriptions_lock:
            # Check direct feature key matches
            feature_subscribers = self._subscriptions_by_feature.get(notification.feature_key, set())
            wildcard_subscribers = self._subscriptions_by_feature.get('*', set())
            
            all_potential_subscribers = feature_subscribers | wildcard_subscribers
            
            for subscription_id in all_potential_subscribers:
                subscription = self._subscriptions.get(subscription_id)
                if subscription and subscription.matches_notification(notification):
                    matching_subscribers.append(subscription_id)
        
        return matching_subscribers
    
    def _deliver_notification(self, subscription_id: str, notification: FeatureFlagChangeNotification) -> bool:
        """
        Deliver notification to a specific subscriber
        
        Args:
            subscription_id: Subscription ID to deliver to
            notification: Notification to deliver
            
        Returns:
            True if delivery was successful
        """
        with self._subscriptions_lock:
            subscription = self._subscriptions.get(subscription_id)
            if not subscription or not subscription.is_active:
                return False
        
        try:
            # Update subscription stats
            subscription.last_notified = datetime.now(timezone.utc)
            subscription.notification_count += 1
            
            # Deliver via callback (primary channel)
            if NotificationChannel.CALLBACK in subscription.channels:
                subscription.callback(notification)
            
            # Additional channels could be implemented here
            # (webhook, email, etc.)
            
            logger.debug(f"Successfully delivered notification {notification.notification_id} to {subscription.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deliver notification {notification.notification_id} to {subscription.service_name}: {e}")
            return False
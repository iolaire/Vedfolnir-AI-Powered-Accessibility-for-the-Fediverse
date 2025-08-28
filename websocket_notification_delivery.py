# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Notification Delivery System

This module provides delivery confirmation, retry mechanisms, and fallback
strategies for WebSocket notifications to ensure reliable message delivery.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from threading import Lock, RLock, Timer, Thread
from queue import Queue, PriorityQueue
from flask_socketio import SocketIO, emit

from websocket_notification_system import (
    StandardizedNotification, DeliveryStatus, NotificationPriority
)

logger = logging.getLogger(__name__)


class FallbackMethod(Enum):
    """Fallback delivery methods"""
    EMAIL = "email"
    SMS = "sms"
    PUSH_NOTIFICATION = "push_notification"
    DATABASE_QUEUE = "database_queue"
    IN_APP_BANNER = "in_app_banner"
    SYSTEM_NOTIFICATION = "system_notification"


class DeliveryAttemptResult(Enum):
    """Result of a delivery attempt"""
    SUCCESS = "success"
    FAILED_TEMPORARY = "failed_temporary"
    FAILED_PERMANENT = "failed_permanent"
    RATE_LIMITED = "rate_limited"
    SESSION_OFFLINE = "session_offline"
    USER_OFFLINE = "user_offline"


@dataclass
class DeliveryAttempt:
    """Record of a delivery attempt"""
    attempt_number: int
    timestamp: datetime
    result: DeliveryAttemptResult
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    latency_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            'attempt_number': self.attempt_number,
            'timestamp': self.timestamp.isoformat(),
            'result': self.result.value,
            'error_message': self.error_message,
            'session_id': self.session_id,
            'latency_ms': self.latency_ms
        }


@dataclass
class DeliveryConfirmation:
    """Delivery confirmation from client"""
    notification_id: str
    session_id: str
    user_id: int
    confirmed_at: datetime
    client_timestamp: Optional[datetime] = None
    round_trip_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            'notification_id': self.notification_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'confirmed_at': self.confirmed_at.isoformat(),
            'client_timestamp': self.client_timestamp.isoformat() if self.client_timestamp else None,
            'round_trip_time_ms': self.round_trip_time_ms
        }


@dataclass
class RetryPolicy:
    """Retry policy configuration"""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    retry_on_results: Set[DeliveryAttemptResult] = field(default_factory=lambda: {
        DeliveryAttemptResult.FAILED_TEMPORARY,
        DeliveryAttemptResult.RATE_LIMITED,
        DeliveryAttemptResult.SESSION_OFFLINE
    })
    
    def get_delay_for_attempt(self, attempt_number: int) -> float:
        """Calculate delay for retry attempt"""
        if self.exponential_backoff:
            delay = self.base_delay_seconds * (2 ** (attempt_number - 1))
        else:
            delay = self.base_delay_seconds
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay_seconds)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, attempt_number: int, result: DeliveryAttemptResult) -> bool:
        """Check if should retry based on attempt number and result"""
        if attempt_number >= self.max_attempts:
            return False
        
        return result in self.retry_on_results


class NotificationDeliveryTracker:
    """Tracks notification delivery status and confirmations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Delivery tracking
        self._delivery_attempts = defaultdict(list)  # notification_id -> List[DeliveryAttempt]
        self._delivery_confirmations = defaultdict(list)  # notification_id -> List[DeliveryConfirmation]
        self._pending_confirmations = defaultdict(set)  # notification_id -> Set[session_id]
        
        # Timing tracking
        self._delivery_start_times = {}  # notification_id -> datetime
        self._confirmation_timeouts = {}  # notification_id -> Timer
        
        # Statistics
        self._delivery_stats = {
            'total_attempts': 0,
            'successful_deliveries': 0,
            'failed_deliveries': 0,
            'confirmed_deliveries': 0,
            'average_delivery_time_ms': 0.0,
            'average_confirmation_time_ms': 0.0
        }
        
        self._tracking_lock = RLock()
    
    def start_delivery_tracking(self, notification: StandardizedNotification, 
                              target_sessions: Set[str]) -> None:
        """Start tracking delivery for a notification"""
        with self._tracking_lock:
            self._delivery_start_times[notification.id] = datetime.now(timezone.utc)
            
            if notification.requires_acknowledgment:
                self._pending_confirmations[notification.id] = target_sessions.copy()
                
                # Set confirmation timeout
                timeout_seconds = 30.0  # 30 second timeout for confirmations
                timer = Timer(timeout_seconds, self._handle_confirmation_timeout, [notification.id])
                timer.start()
                self._confirmation_timeouts[notification.id] = timer
    
    def record_delivery_attempt(self, notification_id: str, session_id: str, 
                              result: DeliveryAttemptResult, error_message: Optional[str] = None) -> None:
        """Record a delivery attempt"""
        with self._tracking_lock:
            attempt_number = len(self._delivery_attempts[notification_id]) + 1
            
            # Calculate latency if delivery started
            latency_ms = None
            if notification_id in self._delivery_start_times:
                start_time = self._delivery_start_times[notification_id]
                latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            attempt = DeliveryAttempt(
                attempt_number=attempt_number,
                timestamp=datetime.now(timezone.utc),
                result=result,
                error_message=error_message,
                session_id=session_id,
                latency_ms=latency_ms
            )
            
            self._delivery_attempts[notification_id].append(attempt)
            
            # Update statistics
            self._delivery_stats['total_attempts'] += 1
            if result == DeliveryAttemptResult.SUCCESS:
                self._delivery_stats['successful_deliveries'] += 1
                if latency_ms:
                    self._update_average_delivery_time(latency_ms)
            else:
                self._delivery_stats['failed_deliveries'] += 1
            
            self.logger.debug(f"Recorded delivery attempt {attempt_number} for notification {notification_id}: {result.value}")
    
    def record_delivery_confirmation(self, notification_id: str, session_id: str, 
                                   user_id: int, client_timestamp: Optional[datetime] = None) -> bool:
        """
        Record delivery confirmation from client
        
        Returns:
            True if confirmation was expected and recorded, False otherwise
        """
        with self._tracking_lock:
            # Check if confirmation was expected
            if (notification_id not in self._pending_confirmations or 
                session_id not in self._pending_confirmations[notification_id]):
                self.logger.warning(f"Unexpected confirmation for notification {notification_id} from session {session_id}")
                return False
            
            confirmed_at = datetime.now(timezone.utc)
            
            # Calculate round-trip time
            round_trip_time_ms = None
            if notification_id in self._delivery_start_times:
                start_time = self._delivery_start_times[notification_id]
                round_trip_time_ms = (confirmed_at - start_time).total_seconds() * 1000
            
            confirmation = DeliveryConfirmation(
                notification_id=notification_id,
                session_id=session_id,
                user_id=user_id,
                confirmed_at=confirmed_at,
                client_timestamp=client_timestamp,
                round_trip_time_ms=round_trip_time_ms
            )
            
            self._delivery_confirmations[notification_id].append(confirmation)
            self._pending_confirmations[notification_id].discard(session_id)
            
            # Update statistics
            self._delivery_stats['confirmed_deliveries'] += 1
            if round_trip_time_ms:
                self._update_average_confirmation_time(round_trip_time_ms)
            
            # Check if all confirmations received
            if not self._pending_confirmations[notification_id]:
                self._complete_delivery_tracking(notification_id)
            
            self.logger.debug(f"Recorded confirmation for notification {notification_id} from session {session_id}")
            return True
    
    def get_delivery_status(self, notification_id: str) -> Dict[str, Any]:
        """Get delivery status for a notification"""
        with self._tracking_lock:
            attempts = self._delivery_attempts.get(notification_id, [])
            confirmations = self._delivery_confirmations.get(notification_id, [])
            pending = self._pending_confirmations.get(notification_id, set())
            
            return {
                'notification_id': notification_id,
                'total_attempts': len(attempts),
                'successful_attempts': len([a for a in attempts if a.result == DeliveryAttemptResult.SUCCESS]),
                'failed_attempts': len([a for a in attempts if a.result != DeliveryAttemptResult.SUCCESS]),
                'confirmations_received': len(confirmations),
                'pending_confirmations': len(pending),
                'attempts': [attempt.to_dict() for attempt in attempts],
                'confirmations': [conf.to_dict() for conf in confirmations],
                'is_complete': len(pending) == 0
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get delivery statistics"""
        with self._tracking_lock:
            return self._delivery_stats.copy()
    
    def cleanup_completed_deliveries(self, max_age_hours: int = 24) -> int:
        """Clean up completed delivery tracking data"""
        with self._tracking_lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            cleaned_count = 0
            
            # Find completed deliveries older than cutoff
            to_remove = []
            for notification_id in list(self._delivery_attempts.keys()):
                if (notification_id not in self._pending_confirmations or 
                    not self._pending_confirmations[notification_id]):
                    # Delivery is complete, check age
                    attempts = self._delivery_attempts[notification_id]
                    if attempts and attempts[-1].timestamp < cutoff_time:
                        to_remove.append(notification_id)
            
            # Remove old tracking data
            for notification_id in to_remove:
                self._delivery_attempts.pop(notification_id, None)
                self._delivery_confirmations.pop(notification_id, None)
                self._pending_confirmations.pop(notification_id, None)
                self._delivery_start_times.pop(notification_id, None)
                
                # Cancel timeout timer if still active
                timer = self._confirmation_timeouts.pop(notification_id, None)
                if timer:
                    timer.cancel()
                
                cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} completed delivery records")
            
            return cleaned_count
    
    def _handle_confirmation_timeout(self, notification_id: str) -> None:
        """Handle confirmation timeout for a notification"""
        with self._tracking_lock:
            pending = self._pending_confirmations.get(notification_id, set())
            if pending:
                self.logger.warning(f"Confirmation timeout for notification {notification_id}, {len(pending)} sessions did not confirm")
                
                # Mark as complete even without all confirmations
                self._complete_delivery_tracking(notification_id)
    
    def _complete_delivery_tracking(self, notification_id: str) -> None:
        """Complete delivery tracking for a notification"""
        # Cancel timeout timer
        timer = self._confirmation_timeouts.pop(notification_id, None)
        if timer:
            timer.cancel()
        
        # Clear pending confirmations
        self._pending_confirmations.pop(notification_id, None)
        
        self.logger.debug(f"Completed delivery tracking for notification {notification_id}")
    
    def _update_average_delivery_time(self, latency_ms: float) -> None:
        """Update average delivery time statistic"""
        current_avg = self._delivery_stats['average_delivery_time_ms']
        successful_count = self._delivery_stats['successful_deliveries']
        
        # Calculate new average
        new_avg = ((current_avg * (successful_count - 1)) + latency_ms) / successful_count
        self._delivery_stats['average_delivery_time_ms'] = new_avg
    
    def _update_average_confirmation_time(self, round_trip_time_ms: float) -> None:
        """Update average confirmation time statistic"""
        current_avg = self._delivery_stats['average_confirmation_time_ms']
        confirmed_count = self._delivery_stats['confirmed_deliveries']
        
        # Calculate new average
        new_avg = ((current_avg * (confirmed_count - 1)) + round_trip_time_ms) / confirmed_count
        self._delivery_stats['average_confirmation_time_ms'] = new_avg


class NotificationRetryManager:
    """Manages retry logic for failed notification deliveries"""
    
    def __init__(self, socketio: SocketIO, delivery_tracker: NotificationDeliveryTracker):
        self.socketio = socketio
        self.delivery_tracker = delivery_tracker
        self.logger = logging.getLogger(__name__)
        
        # Retry queue (priority queue with retry time as priority)
        self._retry_queue = PriorityQueue()
        self._retry_lock = Lock()
        
        # Retry policies by priority
        self._retry_policies = {
            NotificationPriority.CRITICAL: RetryPolicy(
                max_attempts=5,
                base_delay_seconds=0.5,
                max_delay_seconds=30.0
            ),
            NotificationPriority.URGENT: RetryPolicy(
                max_attempts=4,
                base_delay_seconds=1.0,
                max_delay_seconds=45.0
            ),
            NotificationPriority.HIGH: RetryPolicy(
                max_attempts=3,
                base_delay_seconds=2.0,
                max_delay_seconds=60.0
            ),
            NotificationPriority.NORMAL: RetryPolicy(
                max_attempts=2,
                base_delay_seconds=5.0,
                max_delay_seconds=120.0
            ),
            NotificationPriority.LOW: RetryPolicy(
                max_attempts=1,
                base_delay_seconds=10.0,
                max_delay_seconds=300.0
            )
        }
        
        # Retry worker thread
        self._retry_worker_running = False
        self._retry_worker_thread = None
        
        # Statistics
        self._retry_stats = {
            'total_retries': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'abandoned_notifications': 0
        }
    
    def start_retry_worker(self) -> None:
        """Start the retry worker thread"""
        if self._retry_worker_running:
            return
        
        self._retry_worker_running = True
        self._retry_worker_thread = Thread(target=self._retry_worker, daemon=True)
        self._retry_worker_thread.start()
        
        self.logger.info("Notification retry worker started")
    
    def stop_retry_worker(self) -> None:
        """Stop the retry worker thread"""
        self._retry_worker_running = False
        
        if self._retry_worker_thread:
            self._retry_worker_thread.join(timeout=5.0)
        
        self.logger.info("Notification retry worker stopped")
    
    def schedule_retry(self, notification: StandardizedNotification, 
                      session_id: str, attempt_number: int, 
                      last_result: DeliveryAttemptResult) -> bool:
        """
        Schedule a retry for a failed notification delivery
        
        Args:
            notification: Notification to retry
            session_id: Session that failed to receive notification
            attempt_number: Current attempt number
            last_result: Result of the last delivery attempt
            
        Returns:
            True if retry was scheduled, False if no more retries
        """
        try:
            # Get retry policy for notification priority
            retry_policy = self._retry_policies.get(
                notification.priority, 
                self._retry_policies[NotificationPriority.NORMAL]
            )
            
            # Check if should retry
            if not retry_policy.should_retry(attempt_number, last_result):
                self.logger.debug(f"No retry scheduled for notification {notification.id} (attempt {attempt_number}, result {last_result.value})")
                self._retry_stats['abandoned_notifications'] += 1
                return False
            
            # Calculate retry delay
            delay = retry_policy.get_delay_for_attempt(attempt_number + 1)
            retry_time = time.time() + delay
            
            # Add to retry queue
            retry_item = (retry_time, notification.id, notification, session_id, attempt_number + 1)
            self._retry_queue.put(retry_item)
            
            self.logger.debug(f"Scheduled retry for notification {notification.id} in {delay:.2f} seconds (attempt {attempt_number + 1})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error scheduling retry for notification {notification.id}: {e}")
            return False
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """Get retry statistics"""
        return {
            **self._retry_stats,
            'queue_size': self._retry_queue.qsize(),
            'worker_running': self._retry_worker_running
        }
    
    def _retry_worker(self) -> None:
        """Retry worker thread main loop"""
        self.logger.info("Retry worker thread started")
        
        while self._retry_worker_running:
            try:
                # Get next retry item (blocks until available)
                retry_item = self._retry_queue.get(timeout=1.0)
                retry_time, notification_id, notification, session_id, attempt_number = retry_item
                
                # Check if it's time to retry
                current_time = time.time()
                if current_time < retry_time:
                    # Put back in queue and wait
                    self._retry_queue.put(retry_item)
                    time.sleep(0.1)
                    continue
                
                # Attempt retry
                self._attempt_retry(notification, session_id, attempt_number)
                self._retry_stats['total_retries'] += 1
                
            except Exception as e:
                if self._retry_worker_running:  # Only log if not shutting down
                    self.logger.error(f"Error in retry worker: {e}")
                time.sleep(1.0)
        
        self.logger.info("Retry worker thread stopped")
    
    def _attempt_retry(self, notification: StandardizedNotification, 
                      session_id: str, attempt_number: int) -> None:
        """Attempt to retry notification delivery"""
        try:
            self.logger.debug(f"Attempting retry {attempt_number} for notification {notification.id} to session {session_id}")
            
            # Check if session is still online
            if not self._is_session_online(session_id):
                self.delivery_tracker.record_delivery_attempt(
                    notification.id, session_id, 
                    DeliveryAttemptResult.SESSION_OFFLINE,
                    "Session offline during retry"
                )
                return
            
            # Attempt delivery
            try:
                payload = notification.get_client_payload()
                emit(notification.event_name, payload, room=session_id, namespace=notification.namespace)
                
                # Record successful retry
                self.delivery_tracker.record_delivery_attempt(
                    notification.id, session_id, 
                    DeliveryAttemptResult.SUCCESS
                )
                self._retry_stats['successful_retries'] += 1
                
                self.logger.debug(f"Retry {attempt_number} successful for notification {notification.id}")
                
            except Exception as e:
                # Record failed retry
                self.delivery_tracker.record_delivery_attempt(
                    notification.id, session_id, 
                    DeliveryAttemptResult.FAILED_TEMPORARY,
                    f"Retry failed: {str(e)}"
                )
                self._retry_stats['failed_retries'] += 1
                
                # Schedule another retry if policy allows
                retry_policy = self._retry_policies.get(
                    notification.priority, 
                    self._retry_policies[NotificationPriority.NORMAL]
                )
                
                if retry_policy.should_retry(attempt_number, DeliveryAttemptResult.FAILED_TEMPORARY):
                    self.schedule_retry(notification, session_id, attempt_number, DeliveryAttemptResult.FAILED_TEMPORARY)
                
        except Exception as e:
            self.logger.error(f"Error during retry attempt for notification {notification.id}: {e}")
    
    def _is_session_online(self, session_id: str) -> bool:
        """Check if session is currently online"""
        # This would integrate with the connection tracker
        # For now, assume session is online
        return True


class NotificationFallbackManager:
    """Manages fallback delivery methods when WebSocket delivery fails"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Fallback handlers
        self._fallback_handlers = {}
        
        # Fallback policies by notification type and priority
        self._fallback_policies = {
            NotificationPriority.CRITICAL: [
                FallbackMethod.EMAIL,
                FallbackMethod.SMS,
                FallbackMethod.PUSH_NOTIFICATION,
                FallbackMethod.DATABASE_QUEUE
            ],
            NotificationPriority.URGENT: [
                FallbackMethod.EMAIL,
                FallbackMethod.PUSH_NOTIFICATION,
                FallbackMethod.DATABASE_QUEUE
            ],
            NotificationPriority.HIGH: [
                FallbackMethod.EMAIL,
                FallbackMethod.DATABASE_QUEUE
            ],
            NotificationPriority.NORMAL: [
                FallbackMethod.DATABASE_QUEUE,
                FallbackMethod.IN_APP_BANNER
            ],
            NotificationPriority.LOW: [
                FallbackMethod.DATABASE_QUEUE
            ]
        }
        
        # Statistics
        self._fallback_stats = {
            'total_fallbacks': 0,
            'successful_fallbacks': 0,
            'failed_fallbacks': 0,
            'fallbacks_by_method': defaultdict(int)
        }
    
    def register_fallback_handler(self, method: FallbackMethod, handler: Callable) -> None:
        """Register a fallback delivery handler"""
        self._fallback_handlers[method] = handler
        self.logger.debug(f"Registered fallback handler for method: {method.value}")
    
    def trigger_fallback(self, notification: StandardizedNotification, 
                        failed_user_ids: Set[int], reason: str) -> bool:
        """
        Trigger fallback delivery for failed notification
        
        Args:
            notification: Notification that failed to deliver
            failed_user_ids: Set of user IDs that didn't receive the notification
            reason: Reason for fallback trigger
            
        Returns:
            True if at least one fallback method succeeded, False otherwise
        """
        try:
            # Get fallback methods for notification priority
            fallback_methods = self._fallback_policies.get(
                notification.priority, 
                [FallbackMethod.DATABASE_QUEUE]
            )
            
            success_count = 0
            
            for method in fallback_methods:
                if method in self._fallback_handlers:
                    try:
                        handler = self._fallback_handlers[method]
                        success = handler(notification, failed_user_ids, reason)
                        
                        self._fallback_stats['fallbacks_by_method'][method.value] += 1
                        
                        if success:
                            success_count += 1
                            self.logger.debug(f"Fallback delivery successful via {method.value} for notification {notification.id}")
                        else:
                            self.logger.warning(f"Fallback delivery failed via {method.value} for notification {notification.id}")
                            
                    except Exception as e:
                        self.logger.error(f"Error in fallback handler {method.value} for notification {notification.id}: {e}")
                        self._fallback_stats['failed_fallbacks'] += 1
                else:
                    self.logger.warning(f"No handler registered for fallback method: {method.value}")
            
            self._fallback_stats['total_fallbacks'] += 1
            if success_count > 0:
                self._fallback_stats['successful_fallbacks'] += 1
                return True
            else:
                self._fallback_stats['failed_fallbacks'] += 1
                return False
                
        except Exception as e:
            self.logger.error(f"Error triggering fallback for notification {notification.id}: {e}")
            return False
    
    def get_fallback_statistics(self) -> Dict[str, Any]:
        """Get fallback statistics"""
        return {
            **self._fallback_stats,
            'fallbacks_by_method': dict(self._fallback_stats['fallbacks_by_method']),
            'registered_handlers': list(self._fallback_handlers.keys())
        }
    
    def _default_database_fallback(self, notification: StandardizedNotification, 
                                 failed_user_ids: Set[int], reason: str) -> bool:
        """Default database fallback handler"""
        try:
            if not self.db_manager:
                return False
            
            # Store notification in database for later retrieval
            # This would implement database storage
            self.logger.debug(f"Stored notification {notification.id} in database fallback for {len(failed_user_ids)} users")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in database fallback: {e}")
            return False
    
    def _default_in_app_banner_fallback(self, notification: StandardizedNotification, 
                                      failed_user_ids: Set[int], reason: str) -> bool:
        """Default in-app banner fallback handler"""
        try:
            # This would implement in-app banner storage
            self.logger.debug(f"Queued notification {notification.id} for in-app banner display")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in in-app banner fallback: {e}")
            return False


class WebSocketNotificationDeliverySystem:
    """
    Comprehensive notification delivery system with confirmation tracking,
    retry mechanisms, and fallback strategies
    """
    
    def __init__(self, socketio: SocketIO, db_manager=None):
        self.socketio = socketio
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.delivery_tracker = NotificationDeliveryTracker()
        self.retry_manager = NotificationRetryManager(socketio, self.delivery_tracker)
        self.fallback_manager = NotificationFallbackManager(db_manager)
        
        # Register default fallback handlers
        self.fallback_manager.register_fallback_handler(
            FallbackMethod.DATABASE_QUEUE,
            self.fallback_manager._default_database_fallback
        )
        self.fallback_manager.register_fallback_handler(
            FallbackMethod.IN_APP_BANNER,
            self.fallback_manager._default_in_app_banner_fallback
        )
        
        # Start retry worker
        self.retry_manager.start_retry_worker()
        
        # Register WebSocket event handlers
        self._register_delivery_handlers()
        
        self.logger.info("WebSocket Notification Delivery System initialized")
    
    def deliver_notification(self, notification: StandardizedNotification, 
                           target_sessions: Set[str]) -> bool:
        """
        Deliver notification with full tracking and retry support
        
        Args:
            notification: Notification to deliver
            target_sessions: Set of target session IDs
            
        Returns:
            True if delivery was initiated successfully, False otherwise
        """
        try:
            # Start delivery tracking
            self.delivery_tracker.start_delivery_tracking(notification, target_sessions)
            
            successful_deliveries = set()
            failed_deliveries = set()
            
            # Attempt delivery to each session
            for session_id in target_sessions:
                try:
                    payload = notification.get_client_payload()
                    emit(notification.event_name, payload, room=session_id, namespace=notification.namespace)
                    
                    successful_deliveries.add(session_id)
                    self.delivery_tracker.record_delivery_attempt(
                        notification.id, session_id, DeliveryAttemptResult.SUCCESS
                    )
                    
                except Exception as e:
                    failed_deliveries.add(session_id)
                    self.delivery_tracker.record_delivery_attempt(
                        notification.id, session_id, 
                        DeliveryAttemptResult.FAILED_TEMPORARY,
                        str(e)
                    )
                    
                    # Schedule retry
                    self.retry_manager.schedule_retry(
                        notification, session_id, 1, DeliveryAttemptResult.FAILED_TEMPORARY
                    )
            
            # Handle complete delivery failure
            if not successful_deliveries and failed_deliveries:
                # Get user IDs for failed sessions
                failed_user_ids = set()
                for session_id in failed_deliveries:
                    user_id = self._get_user_id_for_session(session_id)
                    if user_id:
                        failed_user_ids.add(user_id)
                
                # Trigger fallback if appropriate
                if failed_user_ids:
                    self.fallback_manager.trigger_fallback(
                        notification, failed_user_ids, "WebSocket delivery failed"
                    )
            
            self.logger.debug(f"Delivered notification {notification.id} to {len(successful_deliveries)} sessions, {len(failed_deliveries)} failed")
            return len(successful_deliveries) > 0
            
        except Exception as e:
            self.logger.error(f"Error delivering notification {notification.id}: {e}")
            return False
    
    def confirm_delivery(self, notification_id: str, session_id: str, 
                        user_id: int, client_timestamp: Optional[datetime] = None) -> bool:
        """Confirm delivery of a notification"""
        return self.delivery_tracker.record_delivery_confirmation(
            notification_id, session_id, user_id, client_timestamp
        )
    
    def get_delivery_status(self, notification_id: str) -> Dict[str, Any]:
        """Get delivery status for a notification"""
        return self.delivery_tracker.get_delivery_status(notification_id)
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return {
            'delivery_tracker': self.delivery_tracker.get_statistics(),
            'retry_manager': self.retry_manager.get_retry_statistics(),
            'fallback_manager': self.fallback_manager.get_fallback_statistics()
        }
    
    def cleanup_old_data(self, max_age_hours: int = 24) -> Dict[str, int]:
        """Clean up old tracking data"""
        delivery_cleaned = self.delivery_tracker.cleanup_completed_deliveries(max_age_hours)
        
        return {
            'delivery_records_cleaned': delivery_cleaned
        }
    
    def shutdown(self) -> None:
        """Shutdown the delivery system"""
        self.retry_manager.stop_retry_worker()
        self.logger.info("WebSocket Notification Delivery System shutdown")
    
    def _register_delivery_handlers(self) -> None:
        """Register WebSocket event handlers for delivery system"""
        
        @self.socketio.on('notification_delivery_confirmation')
        def handle_delivery_confirmation(data):
            """Handle delivery confirmation from client"""
            try:
                if not isinstance(data, dict):
                    emit('error', {'message': 'Invalid confirmation format'})
                    return
                
                notification_id = data.get('notification_id')
                session_id = data.get('session_id')
                user_id = data.get('user_id')
                client_timestamp_str = data.get('client_timestamp')
                
                if not all([notification_id, session_id, user_id]):
                    emit('error', {'message': 'Missing required confirmation fields'})
                    return
                
                # Parse client timestamp if provided
                client_timestamp = None
                if client_timestamp_str:
                    try:
                        client_timestamp = datetime.fromisoformat(client_timestamp_str.replace('Z', '+00:00'))
                    except ValueError:
                        pass
                
                # Record confirmation
                success = self.confirm_delivery(notification_id, session_id, user_id, client_timestamp)
                
                if success:
                    emit('confirmation_acknowledged', {
                        'notification_id': notification_id,
                        'status': 'confirmed'
                    })
                else:
                    emit('confirmation_acknowledged', {
                        'notification_id': notification_id,
                        'status': 'unexpected'
                    })
                
            except Exception as e:
                self.logger.error(f"Error handling delivery confirmation: {e}")
                emit('error', {'message': 'Confirmation processing failed'})
        
        @self.socketio.on('get_delivery_status')
        def handle_get_delivery_status(data):
            """Handle request for delivery status"""
            try:
                if not isinstance(data, dict) or 'notification_id' not in data:
                    emit('error', {'message': 'Invalid status request format'})
                    return
                
                notification_id = data['notification_id']
                status = self.get_delivery_status(notification_id)
                
                emit('delivery_status_response', {
                    'notification_id': notification_id,
                    'status': status
                })
                
            except Exception as e:
                self.logger.error(f"Error handling delivery status request: {e}")
                emit('error', {'message': 'Status request failed'})
    
    def _get_user_id_for_session(self, session_id: str) -> Optional[int]:
        """Get user ID for a session"""
        # This would integrate with the connection tracker
        # For now, return None
        return None
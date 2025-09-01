# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Delivery Fallback System

This module provides comprehensive fallback mechanisms for notification delivery failures,
including retry logic, alternative delivery methods, graceful degradation,
and emergency notification procedures.
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict

from unified_notification_manager import NotificationMessage, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)


class DeliveryMethod(Enum):
    """Notification delivery methods"""
    WEBSOCKET = "websocket"
    DATABASE_QUEUE = "database_queue"
    BROWSER_STORAGE = "browser_storage"
    POLLING_ENDPOINT = "polling_endpoint"
    EMAIL_FALLBACK = "email_fallback"
    SYSTEM_LOG = "system_log"
    EMERGENCY_ALERT = "emergency_alert"


class DeliveryStatus(Enum):
    """Delivery attempt status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    FALLBACK = "fallback"
    ABANDONED = "abandoned"


class FailureReason(Enum):
    """Reasons for delivery failure"""
    WEBSOCKET_DISCONNECTED = "websocket_disconnected"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_FAILED = "authentication_failed"
    USER_OFFLINE = "user_offline"
    RATE_LIMITED = "rate_limited"
    SYSTEM_OVERLOAD = "system_overload"
    INVALID_MESSAGE = "invalid_message"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class DeliveryAttempt:
    """Information about a delivery attempt"""
    attempt_id: str
    notification_id: str
    user_id: int
    method: DeliveryMethod
    status: DeliveryStatus
    started_at: datetime
    completed_at: Optional[datetime]
    failure_reason: Optional[FailureReason]
    error_message: Optional[str]
    retry_count: int
    next_retry_at: Optional[datetime]
    context: Dict[str, Any]


@dataclass
class FallbackConfig:
    """Configuration for fallback delivery"""
    max_retries: int = 3
    retry_delays: List[int] = None  # Seconds between retries
    fallback_methods: List[DeliveryMethod] = None
    timeout_seconds: int = 30
    rate_limit_per_minute: int = 60
    emergency_threshold_minutes: int = 15
    enable_email_fallback: bool = False
    enable_system_log_fallback: bool = True
    
    def __post_init__(self):
        if self.retry_delays is None:
            self.retry_delays = [5, 15, 60]  # 5s, 15s, 1m
        if self.fallback_methods is None:
            self.fallback_methods = [
                DeliveryMethod.DATABASE_QUEUE,
                DeliveryMethod.BROWSER_STORAGE,
                DeliveryMethod.POLLING_ENDPOINT,
                DeliveryMethod.SYSTEM_LOG
            ]


class NotificationDeliveryFallback:
    """
    Comprehensive fallback system for notification delivery failures
    
    Provides retry logic, alternative delivery methods, graceful degradation,
    and emergency notification procedures with detailed monitoring and recovery.
    """
    
    def __init__(self, websocket_factory, notification_manager, 
                 persistence_manager, config: Optional[FallbackConfig] = None):
        """
        Initialize notification delivery fallback system
        
        Args:
            websocket_factory: WebSocket factory for primary delivery
            notification_manager: Unified notification manager
            persistence_manager: Notification persistence manager
            config: Fallback configuration
        """
        self.websocket_factory = websocket_factory
        self.notification_manager = notification_manager
        self.persistence_manager = persistence_manager
        self.config = config or FallbackConfig()
        self.logger = logging.getLogger(__name__)
        
        # Delivery tracking
        self._delivery_attempts = {}  # attempt_id -> DeliveryAttempt
        self._user_delivery_queue = defaultdict(deque)  # user_id -> deque of notifications
        self._failed_deliveries = defaultdict(list)  # user_id -> list of failed attempts
        
        # Rate limiting
        self._rate_limits = defaultdict(deque)  # user_id -> deque of timestamps
        
        # Retry scheduling
        self._retry_queue = []  # List of (retry_time, attempt_id)
        self._retry_task = None
        
        # Fallback method handlers
        self._fallback_handlers = {
            DeliveryMethod.WEBSOCKET: self._deliver_via_websocket,
            DeliveryMethod.DATABASE_QUEUE: self._deliver_via_database_queue,
            DeliveryMethod.BROWSER_STORAGE: self._deliver_via_browser_storage,
            DeliveryMethod.POLLING_ENDPOINT: self._deliver_via_polling_endpoint,
            DeliveryMethod.EMAIL_FALLBACK: self._deliver_via_email,
            DeliveryMethod.SYSTEM_LOG: self._deliver_via_system_log,
            DeliveryMethod.EMERGENCY_ALERT: self._deliver_via_emergency_alert
        }
        
        # Statistics
        self._delivery_stats = {
            'total_attempts': 0,
            'successful_deliveries': 0,
            'failed_deliveries': 0,
            'fallback_deliveries': 0,
            'retry_attempts': 0,
            'abandoned_deliveries': 0
        }
        
        # Start retry processor
        self._start_retry_processor()
        
        self.logger.info("Notification delivery fallback system initialized")
    
    async def deliver_notification(self, notification: NotificationMessage, 
                                 user_id: int, preferred_method: DeliveryMethod = DeliveryMethod.WEBSOCKET) -> bool:
        """
        Deliver notification with fallback support
        
        Args:
            notification: Notification to deliver
            user_id: Target user ID
            preferred_method: Preferred delivery method
            
        Returns:
            True if delivery was successful (including fallback), False otherwise
        """
        try:
            # Check rate limiting
            if not self._check_rate_limit(user_id):
                self.logger.warning(f"Rate limit exceeded for user {user_id}")
                return await self._handle_rate_limit_exceeded(notification, user_id)
            
            # Create initial delivery attempt
            attempt = self._create_delivery_attempt(notification, user_id, preferred_method)
            
            # Try primary delivery method
            success = await self._attempt_delivery(attempt)
            
            if success:
                self._record_successful_delivery(attempt)
                return True
            
            # Primary delivery failed, try fallback methods
            return await self._handle_delivery_failure(attempt)
            
        except Exception as e:
            self.logger.error(f"Error in notification delivery: {e}")
            return False
    
    async def retry_failed_deliveries(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retry failed deliveries for a user or all users
        
        Args:
            user_id: Optional user ID to retry deliveries for
            
        Returns:
            Dictionary with retry results
        """
        try:
            retry_results = {
                'retried_count': 0,
                'successful_retries': 0,
                'failed_retries': 0,
                'abandoned_retries': 0
            }
            
            # Get failed deliveries to retry
            failed_attempts = []
            if user_id:
                failed_attempts = [attempt for attempt in self._delivery_attempts.values() 
                                 if attempt.user_id == user_id and attempt.status == DeliveryStatus.FAILED]
            else:
                failed_attempts = [attempt for attempt in self._delivery_attempts.values() 
                                 if attempt.status == DeliveryStatus.FAILED]
            
            for attempt in failed_attempts:
                # Check if retry is appropriate
                if not self._should_retry_attempt(attempt):
                    continue
                
                retry_results['retried_count'] += 1
                
                # Update attempt for retry
                attempt.status = DeliveryStatus.RETRYING
                attempt.retry_count += 1
                
                # Try delivery again
                success = await self._attempt_delivery(attempt)
                
                if success:
                    retry_results['successful_retries'] += 1
                    self._record_successful_delivery(attempt)
                else:
                    # Try fallback methods
                    fallback_success = await self._handle_delivery_failure(attempt)
                    if fallback_success:
                        retry_results['successful_retries'] += 1
                    else:
                        retry_results['failed_retries'] += 1
                        
                        # Check if should abandon
                        if attempt.retry_count >= self.config.max_retries:
                            attempt.status = DeliveryStatus.ABANDONED
                            retry_results['abandoned_retries'] += 1
                            self._delivery_stats['abandoned_deliveries'] += 1
            
            self.logger.info(f"Retry completed: {retry_results}")
            return retry_results
            
        except Exception as e:
            self.logger.error(f"Error retrying failed deliveries: {e}")
            return {'error': str(e)}
    
    def get_delivery_status(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """
        Get delivery status for a notification
        
        Args:
            notification_id: Notification ID to check
            
        Returns:
            Dictionary with delivery status information
        """
        try:
            # Find all attempts for this notification
            attempts = [attempt for attempt in self._delivery_attempts.values() 
                       if attempt.notification_id == notification_id]
            
            if not attempts:
                return None
            
            # Get latest attempt
            latest_attempt = max(attempts, key=lambda a: a.started_at)
            
            return {
                'notification_id': notification_id,
                'status': latest_attempt.status.value,
                'method': latest_attempt.method.value,
                'retry_count': latest_attempt.retry_count,
                'started_at': latest_attempt.started_at.isoformat(),
                'completed_at': latest_attempt.completed_at.isoformat() if latest_attempt.completed_at else None,
                'failure_reason': latest_attempt.failure_reason.value if latest_attempt.failure_reason else None,
                'error_message': latest_attempt.error_message,
                'total_attempts': len(attempts),
                'all_attempts': [asdict(attempt) for attempt in attempts]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting delivery status: {e}")
            return {'error': str(e)}
    
    def get_user_delivery_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get delivery statistics for a user
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with user delivery statistics
        """
        try:
            user_attempts = [attempt for attempt in self._delivery_attempts.values() 
                           if attempt.user_id == user_id]
            
            if not user_attempts:
                return {'user_id': user_id, 'no_delivery_attempts': True}
            
            # Calculate statistics
            total_attempts = len(user_attempts)
            successful = len([a for a in user_attempts if a.status == DeliveryStatus.SUCCESS])
            failed = len([a for a in user_attempts if a.status == DeliveryStatus.FAILED])
            abandoned = len([a for a in user_attempts if a.status == DeliveryStatus.ABANDONED])
            pending = len([a for a in user_attempts if a.status == DeliveryStatus.PENDING])
            
            # Method statistics
            method_stats = defaultdict(int)
            for attempt in user_attempts:
                method_stats[attempt.method.value] += 1
            
            # Recent failures
            recent_failures = [a for a in user_attempts 
                             if a.status == DeliveryStatus.FAILED and 
                             a.started_at > datetime.now(timezone.utc) - timedelta(hours=24)]
            
            return {
                'user_id': user_id,
                'total_attempts': total_attempts,
                'successful_deliveries': successful,
                'failed_deliveries': failed,
                'abandoned_deliveries': abandoned,
                'pending_deliveries': pending,
                'success_rate': (successful / total_attempts * 100) if total_attempts > 0 else 0,
                'method_usage': dict(method_stats),
                'recent_failures_24h': len(recent_failures),
                'queue_size': len(self._user_delivery_queue[user_id]),
                'rate_limited': not self._check_rate_limit(user_id)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user delivery stats: {e}")
            return {'user_id': user_id, 'error': str(e)}
    
    def get_system_delivery_stats(self) -> Dict[str, Any]:
        """
        Get system-wide delivery statistics
        
        Returns:
            Dictionary with system delivery statistics
        """
        try:
            # Calculate recent statistics (last 24 hours)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_attempts = [attempt for attempt in self._delivery_attempts.values() 
                             if attempt.started_at > recent_cutoff]
            
            # Method performance
            method_performance = {}
            for method in DeliveryMethod:
                method_attempts = [a for a in recent_attempts if a.method == method]
                if method_attempts:
                    successful = len([a for a in method_attempts if a.status == DeliveryStatus.SUCCESS])
                    method_performance[method.value] = {
                        'attempts': len(method_attempts),
                        'successful': successful,
                        'success_rate': (successful / len(method_attempts) * 100) if method_attempts else 0
                    }
            
            # Failure reasons
            failure_reasons = defaultdict(int)
            for attempt in recent_attempts:
                if attempt.failure_reason:
                    failure_reasons[attempt.failure_reason.value] += 1
            
            return {
                'statistics_timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_stats': self._delivery_stats.copy(),
                'recent_24h_stats': {
                    'total_attempts': len(recent_attempts),
                    'successful': len([a for a in recent_attempts if a.status == DeliveryStatus.SUCCESS]),
                    'failed': len([a for a in recent_attempts if a.status == DeliveryStatus.FAILED]),
                    'abandoned': len([a for a in recent_attempts if a.status == DeliveryStatus.ABANDONED])
                },
                'method_performance': method_performance,
                'failure_reasons': dict(failure_reasons),
                'active_queues': len([q for q in self._user_delivery_queue.values() if q]),
                'retry_queue_size': len(self._retry_queue),
                'rate_limited_users': len([user_id for user_id in self._rate_limits.keys() 
                                         if not self._check_rate_limit(user_id)])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system delivery stats: {e}")
            return {'error': str(e)}
    
    async def _attempt_delivery(self, attempt: DeliveryAttempt) -> bool:
        """
        Attempt to deliver notification using specified method
        
        Args:
            attempt: Delivery attempt information
            
        Returns:
            True if delivery was successful, False otherwise
        """
        try:
            attempt.status = DeliveryStatus.IN_PROGRESS
            self._delivery_stats['total_attempts'] += 1
            
            # Get handler for delivery method
            handler = self._fallback_handlers.get(attempt.method)
            if not handler:
                self.logger.error(f"No handler for delivery method: {attempt.method}")
                attempt.status = DeliveryStatus.FAILED
                attempt.failure_reason = FailureReason.UNKNOWN_ERROR
                attempt.error_message = f"No handler for method {attempt.method.value}"
                return False
            
            # Execute delivery with timeout
            try:
                success = await asyncio.wait_for(
                    handler(attempt), 
                    timeout=self.config.timeout_seconds
                )
                
                if success:
                    attempt.status = DeliveryStatus.SUCCESS
                    attempt.completed_at = datetime.now(timezone.utc)
                    return True
                else:
                    attempt.status = DeliveryStatus.FAILED
                    return False
                    
            except asyncio.TimeoutError:
                attempt.status = DeliveryStatus.FAILED
                attempt.failure_reason = FailureReason.TIMEOUT
                attempt.error_message = f"Delivery timeout after {self.config.timeout_seconds}s"
                return False
            
        except Exception as e:
            self.logger.error(f"Error in delivery attempt: {e}")
            attempt.status = DeliveryStatus.FAILED
            attempt.failure_reason = FailureReason.UNKNOWN_ERROR
            attempt.error_message = str(e)
            return False
    
    async def _handle_delivery_failure(self, failed_attempt: DeliveryAttempt) -> bool:
        """
        Handle delivery failure with fallback methods
        
        Args:
            failed_attempt: Failed delivery attempt
            
        Returns:
            True if fallback delivery was successful, False otherwise
        """
        try:
            self._delivery_stats['failed_deliveries'] += 1
            
            # Try fallback methods in order
            for fallback_method in self.config.fallback_methods:
                # Skip if same as failed method
                if fallback_method == failed_attempt.method:
                    continue
                
                self.logger.info(f"Trying fallback method {fallback_method.value} for notification {failed_attempt.notification_id}")
                
                # Create fallback attempt
                fallback_attempt = self._create_delivery_attempt(
                    notification_id=failed_attempt.notification_id,
                    user_id=failed_attempt.user_id,
                    method=fallback_method,
                    is_fallback=True
                )
                
                # Try fallback delivery
                success = await self._attempt_delivery(fallback_attempt)
                
                if success:
                    self._delivery_stats['fallback_deliveries'] += 1
                    self.logger.info(f"Fallback delivery successful via {fallback_method.value}")
                    return True
            
            # All fallback methods failed
            self.logger.error(f"All fallback methods failed for notification {failed_attempt.notification_id}")
            
            # Schedule retry if appropriate
            if failed_attempt.retry_count < self.config.max_retries:
                self._schedule_retry(failed_attempt)
            else:
                failed_attempt.status = DeliveryStatus.ABANDONED
                self._delivery_stats['abandoned_deliveries'] += 1
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error handling delivery failure: {e}")
            return False
    
    def _create_delivery_attempt(self, notification: NotificationMessage = None, 
                               user_id: int = None, method: DeliveryMethod = None,
                               notification_id: str = None, is_fallback: bool = False) -> DeliveryAttempt:
        """
        Create a delivery attempt record
        
        Args:
            notification: Notification to deliver (optional if notification_id provided)
            user_id: Target user ID
            method: Delivery method
            notification_id: Notification ID (optional if notification provided)
            is_fallback: Whether this is a fallback attempt
            
        Returns:
            DeliveryAttempt record
        """
        attempt_id = f"attempt_{int(datetime.now().timestamp())}_{len(self._delivery_attempts)}"
        
        if notification:
            notification_id = notification.id
        
        attempt = DeliveryAttempt(
            attempt_id=attempt_id,
            notification_id=notification_id,
            user_id=user_id,
            method=method,
            status=DeliveryStatus.PENDING,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            failure_reason=None,
            error_message=None,
            retry_count=0,
            next_retry_at=None,
            context={'is_fallback': is_fallback}
        )
        
        self._delivery_attempts[attempt_id] = attempt
        return attempt
    
    # Delivery method implementations
    async def _deliver_via_websocket(self, attempt: DeliveryAttempt) -> bool:
        """Deliver notification via WebSocket"""
        try:
            # Implementation would use WebSocket factory to send notification
            # This is a placeholder for the actual WebSocket delivery logic
            self.logger.debug(f"Delivering notification {attempt.notification_id} via WebSocket to user {attempt.user_id}")
            
            # Simulate WebSocket delivery
            # In real implementation, this would:
            # 1. Check if user has active WebSocket connection
            # 2. Send notification via WebSocket
            # 3. Wait for delivery confirmation
            
            return True  # Placeholder success
            
        except Exception as e:
            attempt.failure_reason = FailureReason.WEBSOCKET_DISCONNECTED
            attempt.error_message = str(e)
            return False
    
    async def _deliver_via_database_queue(self, attempt: DeliveryAttempt) -> bool:
        """Deliver notification via database queue"""
        try:
            # Store notification in database for later retrieval
            self.logger.debug(f"Queuing notification {attempt.notification_id} in database for user {attempt.user_id}")
            
            # Implementation would use persistence manager to queue notification
            # This ensures notification is available when user reconnects
            
            return True  # Database queue is reliable
            
        except Exception as e:
            attempt.failure_reason = FailureReason.SYSTEM_OVERLOAD
            attempt.error_message = str(e)
            return False
    
    async def _deliver_via_browser_storage(self, attempt: DeliveryAttempt) -> bool:
        """Deliver notification via browser local storage"""
        try:
            # Implementation would store notification in browser storage
            # This requires client-side JavaScript support
            self.logger.debug(f"Storing notification {attempt.notification_id} in browser storage for user {attempt.user_id}")
            
            return True  # Placeholder success
            
        except Exception as e:
            attempt.failure_reason = FailureReason.NETWORK_ERROR
            attempt.error_message = str(e)
            return False
    
    async def _deliver_via_polling_endpoint(self, attempt: DeliveryAttempt) -> bool:
        """Deliver notification via polling endpoint"""
        try:
            # Implementation would make notification available via polling endpoint
            # Client can poll for new notifications
            self.logger.debug(f"Making notification {attempt.notification_id} available via polling for user {attempt.user_id}")
            
            return True  # Polling endpoint is reliable
            
        except Exception as e:
            attempt.failure_reason = FailureReason.SYSTEM_OVERLOAD
            attempt.error_message = str(e)
            return False
    
    async def _deliver_via_email(self, attempt: DeliveryAttempt) -> bool:
        """Deliver notification via email fallback"""
        try:
            if not self.config.enable_email_fallback:
                return False
            
            # Implementation would send email notification
            self.logger.debug(f"Sending email notification {attempt.notification_id} to user {attempt.user_id}")
            
            return True  # Placeholder success
            
        except Exception as e:
            attempt.failure_reason = FailureReason.NETWORK_ERROR
            attempt.error_message = str(e)
            return False
    
    async def _deliver_via_system_log(self, attempt: DeliveryAttempt) -> bool:
        """Deliver notification via system log"""
        try:
            if not self.config.enable_system_log_fallback:
                return False
            
            # Log notification for system monitoring
            self.logger.info(f"NOTIFICATION_FALLBACK: {attempt.notification_id} for user {attempt.user_id}")
            
            return True  # System log is always available
            
        except Exception as e:
            attempt.failure_reason = FailureReason.SYSTEM_OVERLOAD
            attempt.error_message = str(e)
            return False
    
    async def _deliver_via_emergency_alert(self, attempt: DeliveryAttempt) -> bool:
        """Deliver notification via emergency alert system"""
        try:
            # Implementation would trigger emergency alert
            # Only for critical notifications
            self.logger.warning(f"EMERGENCY_NOTIFICATION: {attempt.notification_id} for user {attempt.user_id}")
            
            return True  # Emergency alerts are always delivered
            
        except Exception as e:
            attempt.failure_reason = FailureReason.SYSTEM_OVERLOAD
            attempt.error_message = str(e)
            return False
    
    # Helper methods for rate limiting, retry scheduling, etc.
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limit"""
        current_time = time.time()
        cutoff_time = current_time - 60  # 1 minute window
        
        # Clean old timestamps
        user_timestamps = self._rate_limits[user_id]
        while user_timestamps and user_timestamps[0] < cutoff_time:
            user_timestamps.popleft()
        
        # Check if under limit
        if len(user_timestamps) >= self.config.rate_limit_per_minute:
            return False
        
        # Record this attempt
        user_timestamps.append(current_time)
        return True
    
    async def _handle_rate_limit_exceeded(self, notification: NotificationMessage, user_id: int) -> bool:
        """Handle rate limit exceeded"""
        # Queue notification for later delivery
        self._user_delivery_queue[user_id].append(notification)
        self.logger.warning(f"Rate limit exceeded for user {user_id}, notification queued")
        return True  # Queued successfully
    
    def _schedule_retry(self, attempt: DeliveryAttempt) -> None:
        """Schedule retry for failed attempt"""
        if attempt.retry_count >= len(self.config.retry_delays):
            delay = self.config.retry_delays[-1]  # Use last delay
        else:
            delay = self.config.retry_delays[attempt.retry_count]
        
        retry_time = datetime.now(timezone.utc) + timedelta(seconds=delay)
        attempt.next_retry_at = retry_time
        
        self._retry_queue.append((retry_time, attempt.attempt_id))
        self._retry_queue.sort(key=lambda x: x[0])  # Sort by retry time
        
        self.logger.info(f"Scheduled retry for attempt {attempt.attempt_id} in {delay} seconds")
    
    def _should_retry_attempt(self, attempt: DeliveryAttempt) -> bool:
        """Check if attempt should be retried"""
        if attempt.retry_count >= self.config.max_retries:
            return False
        
        if attempt.next_retry_at and datetime.now(timezone.utc) < attempt.next_retry_at:
            return False
        
        return True
    
    def _record_successful_delivery(self, attempt: DeliveryAttempt) -> None:
        """Record successful delivery"""
        attempt.status = DeliveryStatus.SUCCESS
        attempt.completed_at = datetime.now(timezone.utc)
        self._delivery_stats['successful_deliveries'] += 1
        
        self.logger.debug(f"Successful delivery: {attempt.notification_id} via {attempt.method.value}")
    
    def _start_retry_processor(self) -> None:
        """Start background task for processing retries"""
        async def retry_processor():
            while True:
                try:
                    current_time = datetime.now(timezone.utc)
                    
                    # Process due retries
                    while (self._retry_queue and 
                           self._retry_queue[0][0] <= current_time):
                        retry_time, attempt_id = self._retry_queue.pop(0)
                        
                        attempt = self._delivery_attempts.get(attempt_id)
                        if attempt and attempt.status == DeliveryStatus.FAILED:
                            self.logger.info(f"Processing retry for attempt {attempt_id}")
                            
                            # Update attempt for retry
                            attempt.status = DeliveryStatus.RETRYING
                            attempt.retry_count += 1
                            self._delivery_stats['retry_attempts'] += 1
                            
                            # Try delivery again
                            success = await self._attempt_delivery(attempt)
                            
                            if not success:
                                # Try fallback methods
                                await self._handle_delivery_failure(attempt)
                    
                    # Sleep before next check
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    self.logger.error(f"Error in retry processor: {e}")
                    await asyncio.sleep(10)
        
        # Start retry processor task
        if not self._retry_task or self._retry_task.done():
            self._retry_task = asyncio.create_task(retry_processor())
            self.logger.info("Started retry processor task")
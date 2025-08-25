# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Event Bus

Provides publish/subscribe event system for configuration changes
with async processing and subscription management.
"""

import asyncio
import threading
import logging
import uuid
from typing import Any, Dict, List, Callable, Optional, Set, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import queue
import concurrent.futures

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Configuration event types"""
    CONFIGURATION_CHANGED = "configuration_changed"
    CONFIGURATION_INVALIDATED = "configuration_invalidated"
    RESTART_REQUIRED = "restart_required"
    CACHE_CLEARED = "cache_cleared"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"


@dataclass
class ConfigurationChangeEvent:
    """Configuration change event"""
    event_type: EventType
    key: str
    old_value: Any
    new_value: Any
    source: str
    timestamp: datetime
    requires_restart: bool = False
    admin_user_id: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ConfigurationInvalidateEvent:
    """Configuration cache invalidation event"""
    event_type: EventType
    key: str
    timestamp: datetime
    reason: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RestartRequiredEvent:
    """Restart required event"""
    event_type: EventType
    keys: List[str]
    timestamp: datetime
    reason: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ServiceEvent:
    """Service lifecycle event"""
    event_type: EventType
    service_name: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# Union type for all event types
ConfigurationEvent = Union[ConfigurationChangeEvent, ConfigurationInvalidateEvent, 
                          RestartRequiredEvent, ServiceEvent]


@dataclass
class Subscription:
    """Event subscription details"""
    subscription_id: str
    event_type: EventType
    key_pattern: str  # Can be specific key or wildcard pattern
    callback: Callable[[ConfigurationEvent], None]
    created_at: datetime
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    is_active: bool = True


class ConfigurationEventBus:
    """
    High-performance event bus for configuration changes
    
    Features:
    - Publish/subscribe pattern with pattern matching
    - Async event processing to prevent blocking
    - Subscription management with unique IDs
    - Event filtering and routing
    - Error handling and retry mechanisms
    - Performance monitoring and statistics
    """
    
    def __init__(self, max_workers: int = 4, queue_size: int = 1000):
        """
        Initialize configuration event bus
        
        Args:
            max_workers: Maximum number of worker threads for async processing
            queue_size: Maximum size of event queue
        """
        self.max_workers = max_workers
        self.queue_size = queue_size
        
        # Subscription management
        self._subscriptions: Dict[str, Subscription] = {}
        self._subscriptions_by_type: Dict[EventType, Set[str]] = {}
        self._subscriptions_by_key: Dict[str, Set[str]] = {}
        self._subscriptions_lock = threading.RLock()
        
        # Event processing
        self._event_queue = queue.Queue(maxsize=queue_size)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._processing_thread = None
        self._shutdown_event = threading.Event()
        
        # Statistics
        self._stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'subscriptions_triggered': 0,
            'callback_errors': 0,
            'queue_full_errors': 0
        }
        self._stats_lock = threading.RLock()
        
        # Start processing thread
        self._start_processing()
    
    def publish(self, event: ConfigurationEvent) -> bool:
        """
        Publish configuration event
        
        Args:
            event: Configuration event to publish
            
        Returns:
            True if event was queued successfully
        """
        try:
            # Add to queue for async processing
            self._event_queue.put_nowait(event)
            
            with self._stats_lock:
                self._stats['events_published'] += 1
            
            logger.debug(f"Published event: {event.event_type.value} for key: {getattr(event, 'key', 'N/A')}")
            return True
            
        except queue.Full:
            logger.error("Event queue is full, dropping event")
            with self._stats_lock:
                self._stats['queue_full_errors'] += 1
            return False
        except Exception as e:
            logger.error(f"Error publishing event: {str(e)}")
            return False
    
    def subscribe(self, event_type: EventType, key_pattern: str, 
                 callback: Callable[[ConfigurationEvent], None]) -> str:
        """
        Subscribe to configuration events
        
        Args:
            event_type: Type of events to subscribe to
            key_pattern: Key pattern to match (specific key or wildcard)
            callback: Callback function to invoke
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        
        subscription = Subscription(
            subscription_id=subscription_id,
            event_type=event_type,
            key_pattern=key_pattern,
            callback=callback,
            created_at=datetime.now(timezone.utc)
        )
        
        with self._subscriptions_lock:
            # Store subscription
            self._subscriptions[subscription_id] = subscription
            
            # Index by event type
            if event_type not in self._subscriptions_by_type:
                self._subscriptions_by_type[event_type] = set()
            self._subscriptions_by_type[event_type].add(subscription_id)
            
            # Index by key pattern
            if key_pattern not in self._subscriptions_by_key:
                self._subscriptions_by_key[key_pattern] = set()
            self._subscriptions_by_key[key_pattern].add(subscription_id)
        
        logger.debug(f"Added subscription {subscription_id} for {event_type.value} on {key_pattern}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove subscription
        
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
            
            # Remove from indexes
            event_type_subs = self._subscriptions_by_type.get(subscription.event_type, set())
            event_type_subs.discard(subscription_id)
            
            key_pattern_subs = self._subscriptions_by_key.get(subscription.key_pattern, set())
            key_pattern_subs.discard(subscription_id)
            
            logger.debug(f"Removed subscription {subscription_id}")
            return True
    
    def get_subscribers(self, event_type: EventType, key: str = None) -> List[str]:
        """
        Get list of subscription IDs for event type and key
        
        Args:
            event_type: Event type to match
            key: Optional key to match
            
        Returns:
            List of subscription IDs
        """
        matching_subscriptions = []
        
        with self._subscriptions_lock:
            # Get subscriptions for this event type
            type_subscriptions = self._subscriptions_by_type.get(event_type, set())
            
            for subscription_id in type_subscriptions:
                subscription = self._subscriptions.get(subscription_id)
                if not subscription or not subscription.is_active:
                    continue
                
                # Check key pattern match
                if key is None or self._matches_pattern(key, subscription.key_pattern):
                    matching_subscriptions.append(subscription_id)
        
        return matching_subscriptions
    
    def get_subscription_info(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription information
        
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
                'event_type': subscription.event_type.value,
                'key_pattern': subscription.key_pattern,
                'created_at': subscription.created_at,
                'last_triggered': subscription.last_triggered,
                'trigger_count': subscription.trigger_count,
                'is_active': subscription.is_active
            }
    
    def list_subscriptions(self, event_type: EventType = None) -> List[Dict[str, Any]]:
        """
        List all subscriptions, optionally filtered by event type
        
        Args:
            event_type: Optional event type filter
            
        Returns:
            List of subscription information dictionaries
        """
        subscriptions = []
        
        with self._subscriptions_lock:
            for subscription in self._subscriptions.values():
                if event_type is None or subscription.event_type == event_type:
                    subscriptions.append({
                        'subscription_id': subscription.subscription_id,
                        'event_type': subscription.event_type.value,
                        'key_pattern': subscription.key_pattern,
                        'created_at': subscription.created_at,
                        'last_triggered': subscription.last_triggered,
                        'trigger_count': subscription.trigger_count,
                        'is_active': subscription.is_active
                    })
        
        return subscriptions
    
    def pause_subscription(self, subscription_id: str) -> bool:
        """
        Pause a subscription (stop triggering callbacks)
        
        Args:
            subscription_id: Subscription ID to pause
            
        Returns:
            True if subscription was found and paused
        """
        with self._subscriptions_lock:
            subscription = self._subscriptions.get(subscription_id)
            if subscription:
                subscription.is_active = False
                logger.debug(f"Paused subscription {subscription_id}")
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
                logger.debug(f"Resumed subscription {subscription_id}")
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics
        
        Returns:
            Dictionary with statistics
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        with self._subscriptions_lock:
            stats['active_subscriptions'] = len([s for s in self._subscriptions.values() if s.is_active])
            stats['total_subscriptions'] = len(self._subscriptions)
        
        stats['queue_size'] = self._event_queue.qsize()
        stats['max_queue_size'] = self.queue_size
        
        return stats
    
    def shutdown(self, timeout: float = 5.0) -> bool:
        """
        Shutdown event bus and cleanup resources
        
        Args:
            timeout: Timeout in seconds to wait for shutdown
            
        Returns:
            True if shutdown completed successfully
        """
        logger.info("Shutting down configuration event bus")
        
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
            self._subscriptions_by_type.clear()
            self._subscriptions_by_key.clear()
        
        logger.info("Configuration event bus shutdown complete")
        return True
    
    def _start_processing(self):
        """Start the event processing thread"""
        self._processing_thread = threading.Thread(target=self._process_events, daemon=True)
        self._processing_thread.start()
        logger.debug("Started event processing thread")
    
    def _process_events(self):
        """Main event processing loop"""
        logger.debug("Event processing thread started")
        
        while not self._shutdown_event.is_set():
            try:
                # Get event from queue with timeout
                try:
                    event = self._event_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process event
                self._handle_event(event)
                
                with self._stats_lock:
                    self._stats['events_processed'] += 1
                
                # Mark task as done
                self._event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in event processing loop: {str(e)}")
                with self._stats_lock:
                    self._stats['events_failed'] += 1
        
        logger.debug("Event processing thread stopped")
    
    def _handle_event(self, event: ConfigurationEvent):
        """
        Handle a single event by notifying subscribers
        
        Args:
            event: Event to handle
        """
        try:
            # Get key from event
            event_key = getattr(event, 'key', None)
            if hasattr(event, 'keys'):  # RestartRequiredEvent
                event_key = '*'  # Match all patterns for restart events
            
            # Find matching subscribers
            subscribers = self.get_subscribers(event.event_type, event_key)
            
            if not subscribers:
                logger.debug(f"No subscribers for event {event.event_type.value}")
                return
            
            # Notify subscribers asynchronously
            for subscription_id in subscribers:
                self._executor.submit(self._notify_subscriber, subscription_id, event)
            
        except Exception as e:
            logger.error(f"Error handling event: {str(e)}")
            with self._stats_lock:
                self._stats['events_failed'] += 1
    
    def _notify_subscriber(self, subscription_id: str, event: ConfigurationEvent):
        """
        Notify a single subscriber
        
        Args:
            subscription_id: Subscription ID to notify
            event: Event to send
        """
        try:
            with self._subscriptions_lock:
                subscription = self._subscriptions.get(subscription_id)
                if not subscription or not subscription.is_active:
                    return
                
                # Update subscription stats
                subscription.last_triggered = datetime.now(timezone.utc)
                subscription.trigger_count += 1
            
            # Call the callback
            subscription.callback(event)
            
            with self._stats_lock:
                self._stats['subscriptions_triggered'] += 1
            
            logger.debug(f"Notified subscriber {subscription_id} for event {event.event_type.value}")
            
        except Exception as e:
            logger.error(f"Error notifying subscriber {subscription_id}: {str(e)}")
            with self._stats_lock:
                self._stats['callback_errors'] += 1
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """
        Check if key matches pattern
        
        Args:
            key: Key to check
            pattern: Pattern to match against
            
        Returns:
            True if key matches pattern
        """
        if pattern == '*':
            return True
        elif pattern == key:
            return True
        elif pattern.endswith('*'):
            prefix = pattern[:-1]
            return key.startswith(prefix)
        elif pattern.startswith('*'):
            suffix = pattern[1:]
            return key.endswith(suffix)
        else:
            return key == pattern
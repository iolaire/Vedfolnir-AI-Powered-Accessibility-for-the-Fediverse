# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Warning Monitor for 80% threshold detection and comprehensive logging.

This service implements warning threshold monitoring, admin dashboard notifications,
background periodic monitoring, and comprehensive logging for all storage events
and state changes as specified in requirement 2.4.
"""

import os
import json
import redis
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from .storage_configuration_service import StorageConfigurationService
from .storage_monitor_service import StorageMonitorService, StorageMetrics
from .storage_limit_enforcer import StorageLimitEnforcer

logger = logging.getLogger(__name__)


class StorageEventType(Enum):
    """Types of storage events for logging"""
    WARNING_THRESHOLD_EXCEEDED = "warning_threshold_exceeded"
    WARNING_THRESHOLD_CLEARED = "warning_threshold_cleared"
    LIMIT_EXCEEDED = "limit_exceeded"
    LIMIT_CLEARED = "limit_cleared"
    MONITORING_STARTED = "monitoring_started"
    MONITORING_STOPPED = "monitoring_stopped"
    MONITORING_ERROR = "monitoring_error"
    PERIODIC_CHECK = "periodic_check"
    CACHE_INVALIDATED = "cache_invalidated"
    CONFIGURATION_CHANGED = "configuration_changed"
    ADMIN_NOTIFICATION_SENT = "admin_notification_sent"
    ADMIN_NOTIFICATION_FAILED = "admin_notification_failed"


@dataclass
class StorageEvent:
    """Storage event data structure for comprehensive logging"""
    event_type: StorageEventType
    timestamp: datetime
    storage_gb: float
    limit_gb: float
    warning_threshold_gb: float
    usage_percentage: float
    is_warning_exceeded: bool
    is_limit_exceeded: bool
    message: str
    additional_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StorageEvent':
        """Create from dictionary"""
        data['event_type'] = StorageEventType(data['event_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class WarningNotification:
    """Warning notification data for admin dashboard"""
    id: str
    created_at: datetime
    storage_gb: float
    limit_gb: float
    warning_threshold_gb: float
    usage_percentage: float
    message: str
    severity: str  # 'warning', 'critical'
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['acknowledged_at'] = self.acknowledged_at.isoformat() if self.acknowledged_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WarningNotification':
        """Create from dictionary loaded from Redis"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data['acknowledged_at']:
            data['acknowledged_at'] = datetime.fromisoformat(data['acknowledged_at'])
        return cls(**data)


class StorageWarningMonitor:
    """
    Storage warning monitor with 80% threshold detection and comprehensive logging.
    
    This service provides:
    - 80% warning threshold detection and logging
    - Admin dashboard warning notifications
    - Background periodic storage monitoring
    - Comprehensive logging for all storage events and state changes
    - Thread-safe operations with proper locking
    """
    
    # Redis keys for storing warning state and notifications
    WARNING_STATE_KEY = "vedfolnir:storage:warning_state"
    WARNING_NOTIFICATIONS_KEY = "vedfolnir:storage:warning_notifications"
    STORAGE_EVENTS_KEY = "vedfolnir:storage:events"
    MONITORING_CONFIG_KEY = "vedfolnir:storage:monitoring_config"
    
    # Default monitoring configuration
    DEFAULT_CHECK_INTERVAL_SECONDS = 300  # 5 minutes
    DEFAULT_EVENT_RETENTION_HOURS = 168   # 7 days
    DEFAULT_NOTIFICATION_RETENTION_HOURS = 72  # 3 days
    
    def __init__(self,
                 config_service: Optional[StorageConfigurationService] = None,
                 monitor_service: Optional[StorageMonitorService] = None,
                 enforcer_service: Optional[StorageLimitEnforcer] = None,
                 redis_client: Optional[redis.Redis] = None,
                 notification_callback: Optional[Callable[[WarningNotification], None]] = None):
        """
        Initialize the storage warning monitor.
        
        Args:
            config_service: Storage configuration service instance
            monitor_service: Storage monitor service instance
            enforcer_service: Storage limit enforcer service instance
            redis_client: Redis client instance (optional, will create if not provided)
            notification_callback: Optional callback for warning notifications
        """
        self.config_service = config_service or StorageConfigurationService()
        self.monitor_service = monitor_service or StorageMonitorService(self.config_service)
        self.enforcer_service = enforcer_service
        self.notification_callback = notification_callback
        
        # Thread safety
        self._monitor_lock = threading.RLock()
        self._event_lock = threading.RLock()
        self._notification_lock = threading.RLock()
        
        # Background monitoring state
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        
        # Warning state tracking
        self._last_warning_state = False
        self._last_limit_state = False
        self._last_check_time: Optional[datetime] = None
        
        # Initialize Redis connection
        self._init_redis_connection(redis_client)
        
        # Load monitoring configuration
        self._load_monitoring_config()
        
        # Initialize event logging
        self._init_event_logging()
        
        logger.info("Storage warning monitor initialized")
    
    def _init_redis_connection(self, redis_client: Optional[redis.Redis] = None) -> None:
        """Initialize Redis connection for state management"""
        if redis_client:
            self.redis_client = redis_client
            try:
                self.redis_client.ping()
                logger.info("Using provided Redis client for warning monitor")
            except Exception as e:
                logger.error(f"Provided Redis client failed ping test: {e}")
                raise
        else:
            # Create Redis client from environment variables
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_db = int(os.getenv('REDIS_DB', 0))
            redis_password = os.getenv('REDIS_PASSWORD')
            redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
            
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    ssl=redis_ssl,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                self.redis_client.ping()
                logger.info(f"Connected to Redis for warning monitor at {redis_host}:{redis_port}")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis for warning monitor: {e}")
                raise
    
    def _load_monitoring_config(self) -> None:
        """Load monitoring configuration from Redis or use defaults"""
        try:
            config_data = self.redis_client.get(self.MONITORING_CONFIG_KEY)
            if config_data:
                config = json.loads(config_data)
                self.check_interval_seconds = config.get('check_interval_seconds', self.DEFAULT_CHECK_INTERVAL_SECONDS)
                self.event_retention_hours = config.get('event_retention_hours', self.DEFAULT_EVENT_RETENTION_HOURS)
                self.notification_retention_hours = config.get('notification_retention_hours', self.DEFAULT_NOTIFICATION_RETENTION_HOURS)
                logger.debug("Loaded monitoring configuration from Redis")
            else:
                # Use defaults and save to Redis
                self.check_interval_seconds = self.DEFAULT_CHECK_INTERVAL_SECONDS
                self.event_retention_hours = self.DEFAULT_EVENT_RETENTION_HOURS
                self.notification_retention_hours = self.DEFAULT_NOTIFICATION_RETENTION_HOURS
                self._save_monitoring_config()
                logger.info("Using default monitoring configuration")
        except Exception as e:
            logger.warning(f"Could not load monitoring config from Redis: {e}")
            # Use defaults
            self.check_interval_seconds = self.DEFAULT_CHECK_INTERVAL_SECONDS
            self.event_retention_hours = self.DEFAULT_EVENT_RETENTION_HOURS
            self.notification_retention_hours = self.DEFAULT_NOTIFICATION_RETENTION_HOURS
    
    def _save_monitoring_config(self) -> None:
        """Save monitoring configuration to Redis"""
        try:
            config = {
                'check_interval_seconds': self.check_interval_seconds,
                'event_retention_hours': self.event_retention_hours,
                'notification_retention_hours': self.notification_retention_hours
            }
            self.redis_client.set(self.MONITORING_CONFIG_KEY, json.dumps(config))
        except Exception as e:
            logger.warning(f"Could not save monitoring config to Redis: {e}")
    
    def _init_event_logging(self) -> None:
        """Initialize event logging system"""
        try:
            # Log monitoring initialization event
            self._log_storage_event(
                event_type=StorageEventType.MONITORING_STARTED,
                message="Storage warning monitor initialized",
                additional_data={
                    'check_interval_seconds': self.check_interval_seconds,
                    'event_retention_hours': self.event_retention_hours,
                    'notification_retention_hours': self.notification_retention_hours
                }
            )
        except Exception as e:
            logger.warning(f"Could not log initialization event: {e}")
    
    def _log_storage_event(self, event_type: StorageEventType, message: str, 
                          metrics: Optional[StorageMetrics] = None,
                          additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a storage event with comprehensive information.
        
        Args:
            event_type: Type of storage event
            message: Event message
            metrics: Optional storage metrics (will fetch if not provided)
            additional_data: Optional additional event data
        """
        with self._event_lock:
            try:
                # Get current metrics if not provided
                if metrics is None:
                    try:
                        metrics = self.monitor_service.get_storage_metrics()
                    except Exception as e:
                        logger.warning(f"Could not get metrics for event logging: {e}")
                        # Create minimal metrics for logging
                        limit_gb = self.config_service.get_max_storage_gb()
                        warning_gb = self.config_service.get_warning_threshold_gb()
                        metrics = StorageMetrics(
                            total_bytes=0,
                            total_gb=0.0,
                            limit_gb=limit_gb,
                            usage_percentage=0.0,
                            is_limit_exceeded=False,
                            is_warning_exceeded=False,
                            last_calculated=datetime.now()
                        )
                
                # Create storage event
                event = StorageEvent(
                    event_type=event_type,
                    timestamp=datetime.now(timezone.utc),
                    storage_gb=metrics.total_gb,
                    limit_gb=metrics.limit_gb,
                    warning_threshold_gb=self.config_service.get_warning_threshold_gb(),
                    usage_percentage=metrics.usage_percentage,
                    is_warning_exceeded=metrics.is_warning_exceeded,
                    is_limit_exceeded=metrics.is_limit_exceeded,
                    message=message,
                    additional_data=additional_data
                )
                
                # Store event in Redis
                event_key = f"{self.STORAGE_EVENTS_KEY}:{event.timestamp.isoformat()}"
                self.redis_client.setex(
                    event_key,
                    timedelta(hours=self.event_retention_hours),
                    json.dumps(event.to_dict())
                )
                
                # Log to application logger
                log_level = logging.WARNING if event_type in [
                    StorageEventType.WARNING_THRESHOLD_EXCEEDED,
                    StorageEventType.LIMIT_EXCEEDED,
                    StorageEventType.MONITORING_ERROR
                ] else logging.INFO
                
                logger.log(log_level, f"Storage Event [{event_type.value}]: {message} "
                          f"(Usage: {metrics.total_gb:.2f}GB/{metrics.limit_gb:.2f}GB, "
                          f"{metrics.usage_percentage:.1f}%)")
                
            except Exception as e:
                logger.error(f"Failed to log storage event: {e}")
    
    def check_warning_threshold(self) -> bool:
        """
        Check if storage usage has exceeded the 80% warning threshold.
        
        This method implements the core warning threshold detection logic
        as specified in requirement 2.4.
        
        Returns:
            bool: True if warning threshold is exceeded, False otherwise
        """
        with self._monitor_lock:
            try:
                # Get current storage metrics
                metrics = self.monitor_service.get_storage_metrics()
                
                # Check warning threshold
                warning_exceeded = metrics.is_warning_exceeded
                limit_exceeded = metrics.is_limit_exceeded
                
                # Track state changes for event logging
                warning_state_changed = warning_exceeded != self._last_warning_state
                limit_state_changed = limit_exceeded != self._last_limit_state
                
                # Log warning threshold events
                if warning_state_changed:
                    if warning_exceeded:
                        self._log_storage_event(
                            event_type=StorageEventType.WARNING_THRESHOLD_EXCEEDED,
                            message=f"Storage usage exceeded warning threshold: "
                                   f"{metrics.total_gb:.2f}GB >= {self.config_service.get_warning_threshold_gb():.2f}GB",
                            metrics=metrics,
                            additional_data={
                                'threshold_percentage': self.config_service._config.warning_threshold_percentage,
                                'previous_state': self._last_warning_state
                            }
                        )
                        
                        # Create admin notification
                        self._create_warning_notification(metrics, 'warning')
                        
                    else:
                        self._log_storage_event(
                            event_type=StorageEventType.WARNING_THRESHOLD_CLEARED,
                            message=f"Storage usage dropped below warning threshold: "
                                   f"{metrics.total_gb:.2f}GB < {self.config_service.get_warning_threshold_gb():.2f}GB",
                            metrics=metrics,
                            additional_data={
                                'threshold_percentage': self.config_service._config.warning_threshold_percentage,
                                'previous_state': self._last_warning_state
                            }
                        )
                
                # Log limit threshold events
                if limit_state_changed:
                    if limit_exceeded:
                        self._log_storage_event(
                            event_type=StorageEventType.LIMIT_EXCEEDED,
                            message=f"Storage usage exceeded limit: "
                                   f"{metrics.total_gb:.2f}GB >= {metrics.limit_gb:.2f}GB",
                            metrics=metrics,
                            additional_data={
                                'previous_state': self._last_limit_state
                            }
                        )
                        
                        # Create critical admin notification
                        self._create_warning_notification(metrics, 'critical')
                        
                    else:
                        self._log_storage_event(
                            event_type=StorageEventType.LIMIT_CLEARED,
                            message=f"Storage usage dropped below limit: "
                                   f"{metrics.total_gb:.2f}GB < {metrics.limit_gb:.2f}GB",
                            metrics=metrics,
                            additional_data={
                                'previous_state': self._last_limit_state
                            }
                        )
                
                # Update state tracking
                self._last_warning_state = warning_exceeded
                self._last_limit_state = limit_exceeded
                self._last_check_time = datetime.now(timezone.utc)
                
                # Log periodic check (only if no state changes to avoid spam)
                if not warning_state_changed and not limit_state_changed:
                    self._log_storage_event(
                        event_type=StorageEventType.PERIODIC_CHECK,
                        message=f"Periodic storage check completed",
                        metrics=metrics,
                        additional_data={
                            'check_interval_seconds': self.check_interval_seconds,
                            'warning_state': warning_exceeded,
                            'limit_state': limit_exceeded
                        }
                    )
                
                return warning_exceeded
                
            except Exception as e:
                logger.error(f"Error checking warning threshold: {e}")
                self._log_storage_event(
                    event_type=StorageEventType.MONITORING_ERROR,
                    message=f"Warning threshold check failed: {str(e)}",
                    additional_data={'error_type': type(e).__name__}
                )
                return False
    
    def _create_warning_notification(self, metrics: StorageMetrics, severity: str) -> None:
        """
        Create a warning notification for the admin dashboard.
        
        Args:
            metrics: Current storage metrics
            severity: Notification severity ('warning' or 'critical')
        """
        with self._notification_lock:
            try:
                # Generate notification ID
                notification_id = f"storage_{severity}_{int(datetime.now(timezone.utc).timestamp())}"
                
                # Create notification message
                if severity == 'critical':
                    message = f"CRITICAL: Storage limit exceeded! {metrics.total_gb:.2f}GB of {metrics.limit_gb:.2f}GB used ({metrics.usage_percentage:.1f}%). Caption generation is blocked."
                else:
                    message = f"WARNING: Storage approaching limit. {metrics.total_gb:.2f}GB of {metrics.limit_gb:.2f}GB used ({metrics.usage_percentage:.1f}%). Consider cleanup."
                
                # Create notification object
                notification = WarningNotification(
                    id=notification_id,
                    created_at=datetime.now(timezone.utc),
                    storage_gb=metrics.total_gb,
                    limit_gb=metrics.limit_gb,
                    warning_threshold_gb=self.config_service.get_warning_threshold_gb(),
                    usage_percentage=metrics.usage_percentage,
                    message=message,
                    severity=severity
                )
                
                # Store notification in Redis
                notification_key = f"{self.WARNING_NOTIFICATIONS_KEY}:{notification_id}"
                self.redis_client.setex(
                    notification_key,
                    timedelta(hours=self.notification_retention_hours),
                    json.dumps(notification.to_dict())
                )
                
                # Call notification callback if provided
                if self.notification_callback:
                    try:
                        self.notification_callback(notification)
                        self._log_storage_event(
                            event_type=StorageEventType.ADMIN_NOTIFICATION_SENT,
                            message=f"Admin notification sent: {severity}",
                            metrics=metrics,
                            additional_data={
                                'notification_id': notification_id,
                                'severity': severity
                            }
                        )
                    except Exception as e:
                        logger.error(f"Notification callback failed: {e}")
                        self._log_storage_event(
                            event_type=StorageEventType.ADMIN_NOTIFICATION_FAILED,
                            message=f"Admin notification callback failed: {str(e)}",
                            metrics=metrics,
                            additional_data={
                                'notification_id': notification_id,
                                'severity': severity,
                                'error_type': type(e).__name__
                            }
                        )
                
                logger.info(f"Created {severity} notification: {notification_id}")
                
            except Exception as e:
                logger.error(f"Failed to create warning notification: {e}")
    
    def get_active_notifications(self) -> List[WarningNotification]:
        """
        Get all active warning notifications for the admin dashboard.
        
        Returns:
            List of active WarningNotification objects
        """
        with self._notification_lock:
            try:
                notifications = []
                
                # Get all notification keys
                pattern = f"{self.WARNING_NOTIFICATIONS_KEY}:*"
                notification_keys = self.redis_client.keys(pattern)
                
                for key in notification_keys:
                    try:
                        notification_data = self.redis_client.get(key)
                        if notification_data:
                            notification_dict = json.loads(notification_data)
                            notification = WarningNotification.from_dict(notification_dict)
                            notifications.append(notification)
                    except Exception as e:
                        logger.warning(f"Could not load notification from key {key}: {e}")
                        continue
                
                # Sort by creation time (newest first)
                notifications.sort(key=lambda n: n.created_at, reverse=True)
                
                return notifications
                
            except Exception as e:
                logger.error(f"Error getting active notifications: {e}")
                return []
    
    def acknowledge_notification(self, notification_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge a warning notification.
        
        Args:
            notification_id: ID of the notification to acknowledge
            acknowledged_by: Username or ID of the person acknowledging
            
        Returns:
            bool: True if notification was acknowledged successfully
        """
        with self._notification_lock:
            try:
                notification_key = f"{self.WARNING_NOTIFICATIONS_KEY}:{notification_id}"
                notification_data = self.redis_client.get(notification_key)
                
                if not notification_data:
                    logger.warning(f"Notification {notification_id} not found for acknowledgment")
                    return False
                
                # Load and update notification
                notification_dict = json.loads(notification_data)
                notification_dict['acknowledged'] = True
                notification_dict['acknowledged_at'] = datetime.now(timezone.utc).isoformat()
                notification_dict['acknowledged_by'] = acknowledged_by
                
                # Save updated notification
                ttl = self.redis_client.ttl(notification_key)
                if ttl > 0:
                    self.redis_client.setex(notification_key, ttl, json.dumps(notification_dict))
                else:
                    self.redis_client.set(notification_key, json.dumps(notification_dict))
                
                logger.info(f"Notification {notification_id} acknowledged by {acknowledged_by}")
                return True
                
            except Exception as e:
                logger.error(f"Error acknowledging notification {notification_id}: {e}")
                return False
    
    def start_background_monitoring(self) -> bool:
        """
        Start background periodic storage monitoring.
        
        This creates a background thread that periodically checks storage usage
        and logs events as specified in the requirements.
        
        Returns:
            bool: True if monitoring started successfully
        """
        with self._monitor_lock:
            if self._monitoring_active:
                logger.warning("Background monitoring is already active")
                return False
            
            try:
                # Reset stop event
                self._stop_monitoring.clear()
                
                # Create and start monitoring thread
                self._monitoring_thread = threading.Thread(
                    target=self._background_monitoring_loop,
                    name="StorageWarningMonitor",
                    daemon=True
                )
                self._monitoring_thread.start()
                
                self._monitoring_active = True
                
                self._log_storage_event(
                    event_type=StorageEventType.MONITORING_STARTED,
                    message=f"Background storage monitoring started (interval: {self.check_interval_seconds}s)",
                    additional_data={
                        'check_interval_seconds': self.check_interval_seconds,
                        'thread_name': self._monitoring_thread.name
                    }
                )
                
                logger.info(f"Started background storage monitoring (interval: {self.check_interval_seconds}s)")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start background monitoring: {e}")
                self._monitoring_active = False
                return False
    
    def stop_background_monitoring(self) -> bool:
        """
        Stop background periodic storage monitoring.
        
        Returns:
            bool: True if monitoring stopped successfully
        """
        with self._monitor_lock:
            if not self._monitoring_active:
                logger.warning("Background monitoring is not active")
                return False
            
            try:
                # Signal monitoring thread to stop
                self._stop_monitoring.set()
                
                # Wait for thread to finish (with timeout)
                if self._monitoring_thread and self._monitoring_thread.is_alive():
                    self._monitoring_thread.join(timeout=10.0)
                    
                    if self._monitoring_thread.is_alive():
                        logger.warning("Monitoring thread did not stop within timeout")
                        return False
                
                self._monitoring_active = False
                self._monitoring_thread = None
                
                self._log_storage_event(
                    event_type=StorageEventType.MONITORING_STOPPED,
                    message="Background storage monitoring stopped",
                    additional_data={'stop_requested': True}
                )
                
                logger.info("Stopped background storage monitoring")
                return True
                
            except Exception as e:
                logger.error(f"Error stopping background monitoring: {e}")
                return False
    
    def _background_monitoring_loop(self) -> None:
        """
        Background monitoring loop that runs in a separate thread.
        
        This method implements the periodic storage monitoring as specified
        in the requirements.
        """
        logger.info("Background storage monitoring loop started")
        
        try:
            while not self._stop_monitoring.is_set():
                try:
                    # Perform warning threshold check
                    self.check_warning_threshold()
                    
                    # Clean up old events and notifications periodically
                    if self._last_check_time:
                        time_since_last_cleanup = datetime.now(timezone.utc) - self._last_check_time
                        if time_since_last_cleanup.total_seconds() > 3600:  # Cleanup every hour
                            self._cleanup_old_data()
                    
                except Exception as e:
                    logger.error(f"Error in background monitoring loop: {e}")
                    self._log_storage_event(
                        event_type=StorageEventType.MONITORING_ERROR,
                        message=f"Background monitoring error: {str(e)}",
                        additional_data={'error_type': type(e).__name__}
                    )
                
                # Wait for next check or stop signal
                if self._stop_monitoring.wait(timeout=self.check_interval_seconds):
                    break  # Stop signal received
                    
        except Exception as e:
            logger.error(f"Fatal error in background monitoring loop: {e}")
        finally:
            logger.info("Background storage monitoring loop stopped")
    
    def _cleanup_old_data(self) -> None:
        """Clean up old events and notifications from Redis"""
        try:
            # Clean up old events
            event_pattern = f"{self.STORAGE_EVENTS_KEY}:*"
            event_keys = self.redis_client.keys(event_pattern)
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.event_retention_hours)
            
            cleaned_events = 0
            for key in event_keys:
                try:
                    # Extract timestamp from key
                    timestamp_str = key.split(':', 2)[-1]
                    event_time = datetime.fromisoformat(timestamp_str)
                    
                    if event_time < cutoff_time:
                        self.redis_client.delete(key)
                        cleaned_events += 1
                except Exception:
                    continue
            
            # Clean up old notifications
            notification_pattern = f"{self.WARNING_NOTIFICATIONS_KEY}:*"
            notification_keys = self.redis_client.keys(notification_pattern)
            
            notification_cutoff = datetime.now(timezone.utc) - timedelta(hours=self.notification_retention_hours)
            
            cleaned_notifications = 0
            for key in notification_keys:
                try:
                    notification_data = self.redis_client.get(key)
                    if notification_data:
                        notification_dict = json.loads(notification_data)
                        created_at = datetime.fromisoformat(notification_dict['created_at'])
                        
                        if created_at < notification_cutoff:
                            self.redis_client.delete(key)
                            cleaned_notifications += 1
                except Exception:
                    continue
            
            if cleaned_events > 0 or cleaned_notifications > 0:
                logger.info(f"Cleaned up {cleaned_events} old events and {cleaned_notifications} old notifications")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_storage_events(self, limit: int = 100, event_type_filter: Optional[StorageEventType] = None) -> List[StorageEvent]:
        """
        Get recent storage events for analysis and reporting.
        
        Args:
            limit: Maximum number of events to return
            event_type_filter: Optional filter by event type
            
        Returns:
            List of StorageEvent objects
        """
        with self._event_lock:
            try:
                events = []
                
                # Get all event keys
                pattern = f"{self.STORAGE_EVENTS_KEY}:*"
                event_keys = self.redis_client.keys(pattern)
                
                # Sort keys by timestamp (newest first)
                event_keys.sort(reverse=True)
                
                for key in event_keys[:limit]:
                    try:
                        event_data = self.redis_client.get(key)
                        if event_data:
                            event_dict = json.loads(event_data)
                            event = StorageEvent.from_dict(event_dict)
                            
                            # Apply event type filter if specified
                            if event_type_filter is None or event.event_type == event_type_filter:
                                events.append(event)
                                
                    except Exception as e:
                        logger.warning(f"Could not load event from key {key}: {e}")
                        continue
                
                return events
                
            except Exception as e:
                logger.error(f"Error getting storage events: {e}")
                return []
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring status and statistics.
        
        Returns:
            Dictionary containing monitoring status information
        """
        with self._monitor_lock:
            try:
                # Get current metrics
                metrics = self.monitor_service.get_storage_metrics()
                
                # Get active notifications count
                active_notifications = self.get_active_notifications()
                unacknowledged_count = sum(1 for n in active_notifications if not n.acknowledged)
                
                # Get recent events count
                recent_events = self.get_storage_events(limit=50)
                warning_events_count = sum(1 for e in recent_events 
                                         if e.event_type in [StorageEventType.WARNING_THRESHOLD_EXCEEDED, 
                                                           StorageEventType.LIMIT_EXCEEDED])
                
                return {
                    'monitoring_active': self._monitoring_active,
                    'check_interval_seconds': self.check_interval_seconds,
                    'last_check_time': self._last_check_time.isoformat() if self._last_check_time else None,
                    'current_storage_gb': metrics.total_gb,
                    'storage_limit_gb': metrics.limit_gb,
                    'warning_threshold_gb': self.config_service.get_warning_threshold_gb(),
                    'usage_percentage': metrics.usage_percentage,
                    'is_warning_exceeded': metrics.is_warning_exceeded,
                    'is_limit_exceeded': metrics.is_limit_exceeded,
                    'active_notifications_count': len(active_notifications),
                    'unacknowledged_notifications_count': unacknowledged_count,
                    'recent_warning_events_count': warning_events_count,
                    'event_retention_hours': self.event_retention_hours,
                    'notification_retention_hours': self.notification_retention_hours
                }
                
            except Exception as e:
                logger.error(f"Error getting monitoring status: {e}")
                return {
                    'monitoring_active': self._monitoring_active,
                    'error': str(e)
                }
    
    def update_monitoring_config(self, check_interval_seconds: Optional[int] = None,
                               event_retention_hours: Optional[int] = None,
                               notification_retention_hours: Optional[int] = None) -> bool:
        """
        Update monitoring configuration.
        
        Args:
            check_interval_seconds: New check interval in seconds
            event_retention_hours: New event retention period in hours
            notification_retention_hours: New notification retention period in hours
            
        Returns:
            bool: True if configuration was updated successfully
        """
        with self._monitor_lock:
            try:
                config_changed = False
                
                if check_interval_seconds is not None and check_interval_seconds > 0:
                    self.check_interval_seconds = check_interval_seconds
                    config_changed = True
                
                if event_retention_hours is not None and event_retention_hours > 0:
                    self.event_retention_hours = event_retention_hours
                    config_changed = True
                
                if notification_retention_hours is not None and notification_retention_hours > 0:
                    self.notification_retention_hours = notification_retention_hours
                    config_changed = True
                
                if config_changed:
                    self._save_monitoring_config()
                    
                    self._log_storage_event(
                        event_type=StorageEventType.CONFIGURATION_CHANGED,
                        message="Monitoring configuration updated",
                        additional_data={
                            'check_interval_seconds': self.check_interval_seconds,
                            'event_retention_hours': self.event_retention_hours,
                            'notification_retention_hours': self.notification_retention_hours
                        }
                    )
                    
                    logger.info("Monitoring configuration updated")
                    return True
                else:
                    logger.warning("No valid configuration changes provided")
                    return False
                    
            except Exception as e:
                logger.error(f"Error updating monitoring configuration: {e}")
                return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of the storage warning monitor.
        
        Returns:
            Dictionary containing health check results
        """
        health = {
            'redis_connected': False,
            'config_service_healthy': False,
            'monitor_service_healthy': False,
            'background_monitoring_active': self._monitoring_active,
            'overall_healthy': False
        }
        
        try:
            # Check Redis connection
            self.redis_client.ping()
            health['redis_connected'] = True
        except Exception as e:
            health['redis_error'] = str(e)
        
        try:
            # Check config service
            self.config_service.validate_storage_config()
            health['config_service_healthy'] = True
        except Exception as e:
            health['config_error'] = str(e)
        
        try:
            # Check monitor service
            self.monitor_service.get_storage_metrics()
            health['monitor_service_healthy'] = True
        except Exception as e:
            health['monitor_error'] = str(e)
        
        # Overall health
        health['overall_healthy'] = all([
            health['redis_connected'],
            health['config_service_healthy'],
            health['monitor_service_healthy']
        ])
        
        return health
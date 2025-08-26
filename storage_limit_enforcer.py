# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Limit Enforcer for managing caption generation blocking based on storage limits.

This service enforces storage limits by blocking caption generation when limits are reached,
integrates with Redis for maintaining blocking state, and provides automatic limit enforcement
with pre-generation storage checks.
"""

import os
import json
import redis
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from storage_configuration_service import StorageConfigurationService
from storage_monitor_service import StorageMonitorService, StorageMetrics

logger = logging.getLogger(__name__)


class StorageCheckResult(Enum):
    """Result of storage check before caption generation"""
    ALLOWED = "allowed"
    ALLOWED_OVERRIDE_ACTIVE = "allowed_override_active"
    BLOCKED_LIMIT_EXCEEDED = "blocked_limit_exceeded"
    BLOCKED_OVERRIDE_EXPIRED = "blocked_override_expired"
    ERROR = "error"


@dataclass
class StorageBlockingState:
    """Storage blocking state information"""
    is_blocked: bool
    reason: str
    blocked_at: Optional[datetime]
    storage_gb: float
    limit_gb: float
    usage_percentage: float
    last_checked: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            'is_blocked': self.is_blocked,
            'reason': self.reason,
            'blocked_at': self.blocked_at.isoformat() if self.blocked_at else None,
            'storage_gb': self.storage_gb,
            'limit_gb': self.limit_gb,
            'usage_percentage': self.usage_percentage,
            'last_checked': self.last_checked.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StorageBlockingState':
        """Create from dictionary loaded from Redis"""
        return cls(
            is_blocked=data['is_blocked'],
            reason=data['reason'],
            blocked_at=datetime.fromisoformat(data['blocked_at']) if data['blocked_at'] else None,
            storage_gb=data['storage_gb'],
            limit_gb=data['limit_gb'],
            usage_percentage=data['usage_percentage'],
            last_checked=datetime.fromisoformat(data['last_checked'])
        )


class StorageLimitEnforcerError(Exception):
    """Base storage limit enforcer error"""
    pass


class StorageCheckError(StorageLimitEnforcerError):
    """Storage check operation failed"""
    pass


class RedisConnectionError(StorageLimitEnforcerError):
    """Redis connection failed"""
    pass


class StorageLimitEnforcer:
    """
    Storage limit enforcement system with Redis-based blocking state management.
    
    This service provides:
    - Pre-generation storage checks with automatic blocking
    - Redis-based blocking state persistence (similar to maintenance mode)
    - Automatic unblocking when storage drops below limit
    - Comprehensive logging and audit trail
    - Thread-safe operations with proper locking
    """
    
    # Redis key for storing blocking state
    STORAGE_BLOCKING_KEY = "vedfolnir:storage:blocking_state"
    
    # Redis key for storing enforcement statistics
    STORAGE_STATS_KEY = "vedfolnir:storage:enforcement_stats"
    
    # Default Redis connection settings
    DEFAULT_REDIS_HOST = "localhost"
    DEFAULT_REDIS_PORT = 6379
    DEFAULT_REDIS_DB = 0
    
    def __init__(self, 
                 config_service: Optional[StorageConfigurationService] = None,
                 monitor_service: Optional[StorageMonitorService] = None,
                 redis_client: Optional[redis.Redis] = None,
                 db_manager=None):
        """
        Initialize the storage limit enforcer.
        
        Args:
            config_service: Storage configuration service instance
            monitor_service: Storage monitor service instance
            redis_client: Redis client instance (optional, will create if not provided)
            db_manager: Database manager for override system integration
        """
        self.config_service = config_service or StorageConfigurationService()
        self.monitor_service = monitor_service or StorageMonitorService(self.config_service)
        
        # Initialize override system if db_manager is provided
        self.override_system = None
        if db_manager:
            try:
                from storage_override_system import StorageOverrideSystem
                self.override_system = StorageOverrideSystem(db_manager, self.config_service, self.monitor_service)
                logger.info("Storage override system integrated with enforcer")
            except ImportError as e:
                logger.warning(f"Could not import StorageOverrideSystem: {e}")
            except Exception as e:
                logger.warning(f"Could not initialize override system: {e}")
        
        # Thread safety
        self._state_lock = threading.RLock()
        self._stats_lock = threading.RLock()
        
        # Initialize Redis connection
        self._init_redis_connection(redis_client)
        
        # Initialize enforcement statistics
        self._stats = {
            'total_checks': 0,
            'blocks_enforced': 0,
            'automatic_unblocks': 0,
            'limit_exceeded_count': 0,
            'override_bypasses': 0,
            'last_block_time': None,
            'last_unblock_time': None,
            'current_blocking_duration': 0
        }
        
        # Load existing stats from Redis
        self._load_stats_from_redis()
        
        logger.info("Storage limit enforcer initialized")
    
    def _init_redis_connection(self, redis_client: Optional[redis.Redis] = None) -> None:
        """
        Initialize Redis connection for blocking state management.
        
        Args:
            redis_client: Optional Redis client instance
            
        Raises:
            RedisConnectionError: If Redis connection fails
        """
        if redis_client:
            self.redis_client = redis_client
            # Test provided Redis connection
            try:
                self.redis_client.ping()
                logger.info("Using provided Redis client")
            except Exception as e:
                logger.error(f"Provided Redis client failed ping test: {e}")
                raise RedisConnectionError(f"Redis connection failed: {e}")
        else:
            # Create Redis client from environment variables
            redis_host = os.getenv('REDIS_HOST', self.DEFAULT_REDIS_HOST)
            redis_port = int(os.getenv('REDIS_PORT', self.DEFAULT_REDIS_PORT))
            redis_db = int(os.getenv('REDIS_DB', self.DEFAULT_REDIS_DB))
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
                
                # Test Redis connection
                self.redis_client.ping()
                logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise RedisConnectionError(f"Redis connection failed: {e}")
    
    def _load_stats_from_redis(self) -> None:
        """Load enforcement statistics from Redis"""
        try:
            stats_data = self.redis_client.get(self.STORAGE_STATS_KEY)
            if stats_data:
                stored_stats = json.loads(stats_data)
                with self._stats_lock:
                    self._stats.update(stored_stats)
                logger.debug("Loaded enforcement statistics from Redis")
        except Exception as e:
            logger.warning(f"Could not load stats from Redis: {e}")
    
    def _save_stats_to_redis(self) -> None:
        """Save enforcement statistics to Redis"""
        try:
            with self._stats_lock:
                stats_json = json.dumps(self._stats, default=str)
                self.redis_client.set(self.STORAGE_STATS_KEY, stats_json)
        except Exception as e:
            logger.warning(f"Could not save stats to Redis: {e}")
    
    def _get_blocking_state_from_redis(self) -> Optional[StorageBlockingState]:
        """
        Get current blocking state from Redis.
        
        Returns:
            StorageBlockingState if exists, None otherwise
        """
        try:
            state_data = self.redis_client.get(self.STORAGE_BLOCKING_KEY)
            if state_data:
                state_dict = json.loads(state_data)
                return StorageBlockingState.from_dict(state_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting blocking state from Redis: {e}")
            # Re-raise the exception so calling methods can handle it appropriately
            raise
    
    def _save_blocking_state_to_redis(self, state: StorageBlockingState) -> bool:
        """
        Save blocking state to Redis.
        
        Args:
            state: StorageBlockingState to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            state_json = json.dumps(state.to_dict())
            result = self.redis_client.set(self.STORAGE_BLOCKING_KEY, state_json)
            return bool(result)
        except Exception as e:
            logger.error(f"Error saving blocking state to Redis: {e}")
            return False
    
    def _clear_blocking_state_from_redis(self) -> bool:
        """
        Clear blocking state from Redis.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.redis_client.delete(self.STORAGE_BLOCKING_KEY)
            return bool(result)
        except Exception as e:
            logger.error(f"Error clearing blocking state from Redis: {e}")
            return False
    
    def check_storage_before_generation(self) -> StorageCheckResult:
        """
        Check storage limits before allowing caption generation.
        
        This method performs pre-generation storage checks and enforces limits
        automatically as specified in requirements 2.4, 2.5, 5.1, 5.2, 5.4.
        
        Returns:
            StorageCheckResult indicating whether generation should be allowed
            
        Raises:
            StorageCheckError: If storage check fails
        """
        with self._state_lock:
            try:
                # Update statistics
                with self._stats_lock:
                    self._stats['total_checks'] += 1
                
                # Get current storage metrics
                metrics = self.monitor_service.get_storage_metrics()
                
                # Clean up expired overrides if override system is available
                if self.override_system:
                    try:
                        self.override_system.cleanup_expired_overrides()
                    except Exception as e:
                        logger.warning(f"Error cleaning up expired overrides: {e}")
                
                # Check if storage limit is exceeded
                if metrics.is_limit_exceeded:
                    logger.warning(f"Storage limit exceeded: {metrics.total_gb:.2f}GB >= {metrics.limit_gb:.2f}GB")
                    
                    # Check if there's an active override
                    if self.override_system and self.override_system.is_override_active():
                        active_override = self.override_system.get_active_override()
                        logger.info(f"Storage limit exceeded but override {active_override.id} is active, allowing generation")
                        with self._stats_lock:
                            self._stats['override_bypasses'] += 1
                        self._save_stats_to_redis()
                        return StorageCheckResult.ALLOWED_OVERRIDE_ACTIVE
                    
                    # Block caption generation
                    self._enforce_storage_limit(metrics, "Storage limit exceeded")
                    
                    with self._stats_lock:
                        self._stats['limit_exceeded_count'] += 1
                    
                    return StorageCheckResult.BLOCKED_LIMIT_EXCEEDED
                
                # Check if we're currently blocked but storage is now under limit
                current_state = self._get_blocking_state_from_redis()
                if current_state and current_state.is_blocked:
                    # Storage is under limit, automatically unblock
                    logger.info(f"Storage under limit ({metrics.total_gb:.2f}GB < {metrics.limit_gb:.2f}GB), automatically unblocking")
                    self._lift_storage_limit_blocking(metrics)
                
                # Log warning if approaching threshold
                if metrics.is_warning_exceeded:
                    logger.warning(f"Storage warning threshold exceeded: {metrics.total_gb:.2f}GB >= {self.config_service.get_warning_threshold_gb():.2f}GB")
                
                # Save updated stats
                self._save_stats_to_redis()
                
                return StorageCheckResult.ALLOWED
                
            except Exception as e:
                logger.error(f"Storage check failed: {e}")
                with self._stats_lock:
                    self._stats['total_checks'] += 1
                self._save_stats_to_redis()
                raise StorageCheckError(f"Storage check failed: {e}")
    
    def block_caption_generation(self, reason: str) -> None:
        """
        Manually block caption generation with specified reason.
        
        Args:
            reason: Reason for blocking caption generation
            
        Raises:
            StorageLimitEnforcerError: If blocking fails
        """
        with self._state_lock:
            try:
                # Get current storage metrics
                metrics = self.monitor_service.get_storage_metrics()
                
                # Create blocking state
                blocking_state = StorageBlockingState(
                    is_blocked=True,
                    reason=reason,
                    blocked_at=datetime.now(timezone.utc),
                    storage_gb=metrics.total_gb,
                    limit_gb=metrics.limit_gb,
                    usage_percentage=metrics.usage_percentage,
                    last_checked=datetime.now(timezone.utc)
                )
                
                # Save to Redis
                if self._save_blocking_state_to_redis(blocking_state):
                    logger.info(f"Caption generation blocked: {reason}")
                    
                    # Update statistics
                    with self._stats_lock:
                        self._stats['blocks_enforced'] += 1
                        self._stats['last_block_time'] = datetime.now(timezone.utc).isoformat()
                    
                    self._save_stats_to_redis()
                else:
                    raise StorageLimitEnforcerError("Failed to save blocking state to Redis")
                    
            except Exception as e:
                logger.error(f"Failed to block caption generation: {e}")
                raise StorageLimitEnforcerError(f"Blocking failed: {e}")
    
    def unblock_caption_generation(self) -> None:
        """
        Manually unblock caption generation.
        
        Raises:
            StorageLimitEnforcerError: If unblocking fails
        """
        with self._state_lock:
            try:
                # Get current storage metrics
                metrics = self.monitor_service.get_storage_metrics()
                
                # Clear blocking state from Redis
                if self._clear_blocking_state_from_redis():
                    logger.info("Caption generation unblocked manually")
                    
                    # Update statistics
                    with self._stats_lock:
                        self._stats['last_unblock_time'] = datetime.now(timezone.utc).isoformat()
                    
                    self._save_stats_to_redis()
                else:
                    raise StorageLimitEnforcerError("Failed to clear blocking state from Redis")
                    
            except Exception as e:
                logger.error(f"Failed to unblock caption generation: {e}")
                raise StorageLimitEnforcerError(f"Unblocking failed: {e}")
    
    def is_caption_generation_blocked(self) -> bool:
        """
        Check if caption generation is currently blocked.
        
        Returns:
            True if blocked, False otherwise
        """
        try:
            blocking_state = self._get_blocking_state_from_redis()
            return blocking_state.is_blocked if blocking_state else False
        except Exception as e:
            logger.error(f"Error checking blocking state: {e}")
            # Default to safe mode (blocked) on error
            return True
    
    def get_block_reason(self) -> Optional[str]:
        """
        Get the reason for current blocking.
        
        Returns:
            Blocking reason string if blocked, None otherwise
        """
        try:
            blocking_state = self._get_blocking_state_from_redis()
            if blocking_state and blocking_state.is_blocked:
                return blocking_state.reason
            return None
        except Exception as e:
            logger.error(f"Error getting blocking state from Redis: {e}")
            return "Error retrieving block reason"
    
    def get_blocking_state(self) -> Optional[StorageBlockingState]:
        """
        Get complete blocking state information.
        
        Returns:
            StorageBlockingState if exists, None otherwise
        """
        return self._get_blocking_state_from_redis()
    
    def trigger_limit_reached_actions(self) -> None:
        """
        Trigger all actions when storage limit is reached.
        
        This method coordinates the response to storage limit being reached,
        including blocking, notifications, and logging.
        """
        try:
            # Get current storage metrics
            metrics = self.monitor_service.get_storage_metrics()
            
            if metrics.is_limit_exceeded:
                logger.warning("Storage limit reached, triggering limit reached actions")
                
                # Enforce storage limit blocking
                self._enforce_storage_limit(metrics, "Automatic enforcement - storage limit reached")
                
                # TODO: Trigger email notifications (will be implemented in task 5)
                # TODO: Trigger user notifications (will be implemented in task 6)
                
                logger.info("Storage limit reached actions completed")
            else:
                logger.debug("Storage limit not exceeded, no actions needed")
                
        except Exception as e:
            logger.error(f"Error triggering limit reached actions: {e}")
    
    def _enforce_storage_limit(self, metrics: StorageMetrics, reason: str) -> None:
        """
        Internal method to enforce storage limit blocking.
        
        Args:
            metrics: Current storage metrics
            reason: Reason for enforcement
        """
        try:
            # Create blocking state
            blocking_state = StorageBlockingState(
                is_blocked=True,
                reason=reason,
                blocked_at=datetime.now(timezone.utc),
                storage_gb=metrics.total_gb,
                limit_gb=metrics.limit_gb,
                usage_percentage=metrics.usage_percentage,
                last_checked=datetime.now(timezone.utc)
            )
            
            # Save to Redis
            if self._save_blocking_state_to_redis(blocking_state):
                logger.info(f"Storage limit enforced: {reason}")
                
                # Update statistics
                with self._stats_lock:
                    self._stats['blocks_enforced'] += 1
                    self._stats['last_block_time'] = datetime.now(timezone.utc).isoformat()
                
                self._save_stats_to_redis()
            else:
                logger.error("Failed to save blocking state during enforcement")
                
        except Exception as e:
            logger.error(f"Error enforcing storage limit: {e}")
    
    def _lift_storage_limit_blocking(self, metrics: StorageMetrics) -> None:
        """
        Internal method to lift storage limit blocking when storage drops below limit.
        
        Args:
            metrics: Current storage metrics
        """
        try:
            # Clear blocking state from Redis
            if self._clear_blocking_state_from_redis():
                logger.info(f"Storage limit blocking lifted automatically (usage: {metrics.total_gb:.2f}GB < {metrics.limit_gb:.2f}GB)")
                
                # Update statistics
                with self._stats_lock:
                    self._stats['automatic_unblocks'] += 1
                    self._stats['last_unblock_time'] = datetime.now(timezone.utc).isoformat()
                
                self._save_stats_to_redis()
            else:
                logger.error("Failed to clear blocking state during automatic unblocking")
                
        except Exception as e:
            logger.error(f"Error lifting storage limit blocking: {e}")
    
    def get_enforcement_statistics(self) -> Dict[str, Any]:
        """
        Get storage limit enforcement statistics.
        
        Returns:
            Dictionary containing enforcement statistics
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        # Add current blocking state
        blocking_state = self._get_blocking_state_from_redis()
        stats['currently_blocked'] = blocking_state.is_blocked if blocking_state else False
        stats['current_block_reason'] = blocking_state.reason if blocking_state and blocking_state.is_blocked else None
        
        # Add current storage metrics
        try:
            metrics = self.monitor_service.get_storage_metrics()
            stats['current_storage_gb'] = metrics.total_gb
            stats['storage_limit_gb'] = metrics.limit_gb
            stats['current_usage_percentage'] = metrics.usage_percentage
            stats['is_limit_exceeded'] = metrics.is_limit_exceeded
            stats['is_warning_exceeded'] = metrics.is_warning_exceeded
        except Exception as e:
            logger.error(f"Error getting current metrics for statistics: {e}")
            stats['metrics_error'] = str(e)
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset enforcement statistics"""
        with self._stats_lock:
            self._stats = {
                'total_checks': 0,
                'blocks_enforced': 0,
                'automatic_unblocks': 0,
                'limit_exceeded_count': 0,
                'last_block_time': None,
                'last_unblock_time': None,
                'current_blocking_duration': 0
            }
        
        self._save_stats_to_redis()
        logger.info("Storage limit enforcement statistics reset")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of the storage limit enforcer.
        
        Returns:
            Dictionary containing health check results
        """
        health = {
            'redis_connected': False,
            'config_service_healthy': False,
            'monitor_service_healthy': False,
            'blocking_state_accessible': False,
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
        
        try:
            # Check blocking state access
            self._get_blocking_state_from_redis()
            health['blocking_state_accessible'] = True
        except Exception as e:
            health['blocking_state_error'] = str(e)
        
        # Overall health
        health['overall_healthy'] = all([
            health['redis_connected'],
            health['config_service_healthy'],
            health['monitor_service_healthy'],
            health['blocking_state_accessible']
        ])
        
        return health
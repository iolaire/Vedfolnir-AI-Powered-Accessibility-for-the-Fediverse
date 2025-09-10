# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Feature Flag Service

Provides centralized feature flag management with real-time updates,
caching for high-performance access, and change notifications.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import uuid

from configuration_service import ConfigurationService
from configuration_event_bus import ConfigurationEventBus, EventType, ConfigurationChangeEvent

logger = logging.getLogger(__name__)


class FeatureFlagState(Enum):
    """Feature flag states"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass
class FeatureFlagInfo:
    """Feature flag information with metadata"""
    key: str
    enabled: bool
    state: FeatureFlagState
    last_updated: datetime
    source: str
    description: Optional[str] = None
    usage_count: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class FeatureFlagUsageMetrics:
    """Feature flag usage metrics"""
    total_checks: int = 0
    enabled_checks: int = 0
    disabled_checks: int = 0
    unique_features_accessed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_reset: datetime = None


class FeatureFlagError(Exception):
    """Base feature flag error"""
    pass


class FeatureFlagNotFoundError(FeatureFlagError):
    """Feature flag not found"""
    pass


class FeatureFlagService:
    """
    Centralized feature flag management service
    
    Features:
    - Real-time feature flag updates
    - High-performance caching
    - Change notifications and subscriptions
    - Usage metrics collection
    - Graceful feature disabling
    - Integration with configuration service
    """
    
    # Default feature flags with descriptions
    DEFAULT_FEATURE_FLAGS = {
        'enable_batch_processing': {
            'default': True,
            'description': 'Enable batch processing endpoints and services'
        },
        'enable_advanced_monitoring': {
            'default': False,
            'description': 'Enable advanced monitoring and metrics collection'
        },
        'enable_auto_retry': {
            'default': True,
            'description': 'Enable automatic retry for failed jobs'
        },
        'enable_performance_optimization': {
            'default': True,
            'description': 'Enable performance optimization features'
        },
        'enable_debug_logging': {
            'default': False,
            'description': 'Enable debug-level logging'
        },
        'enable_experimental_features': {
            'default': False,
            'description': 'Enable experimental features (use with caution)'
        }
    }
    
    def __init__(self, config_service: ConfigurationService, event_bus: ConfigurationEventBus = None,
                 cache_ttl: int = 60, metrics_enabled: bool = True):
        """
        Initialize feature flag service
        
        Args:
            config_service: Configuration service instance
            event_bus: Optional event bus for change notifications
            cache_ttl: Cache TTL in seconds
            metrics_enabled: Enable usage metrics collection
        """
        self.config_service = config_service
        self.event_bus = event_bus
        self.cache_ttl = cache_ttl
        self.metrics_enabled = metrics_enabled
        
        # Feature flag cache
        self._flag_cache: Dict[str, FeatureFlagInfo] = {}
        self._cache_lock = threading.RLock()
        
        # Change subscribers
        self._change_subscribers: Dict[str, Dict[str, Callable]] = {}
        self._subscribers_lock = threading.RLock()
        
        # Usage metrics
        self._usage_metrics = FeatureFlagUsageMetrics(
            last_reset=datetime.now(timezone.utc)
        )
        self._metrics_lock = threading.RLock()
        
        # Subscribe to configuration changes if event bus is available
        if self.event_bus:
            self._setup_change_subscriptions()
        
        # Initialize cache with default flags
        self._initialize_default_flags()
    
    def is_enabled(self, feature: str) -> bool:
        """
        Check if a feature flag is enabled
        
        Args:
            feature: Feature flag key
            
        Returns:
            True if feature is enabled, False otherwise
        """
        try:
            flag_info = self._get_flag_info(feature)
            
            # Update usage metrics
            if self.metrics_enabled:
                self._update_usage_metrics(feature, flag_info.enabled)
            
            return flag_info.enabled
            
        except Exception as e:
            logger.error(f"Error checking feature flag {feature}: {str(e)}")
            # Return default value for known flags, False for unknown
            default_info = self.DEFAULT_FEATURE_FLAGS.get(feature, {})
            return default_info.get('default', False)
    
    def get_all_flags(self) -> Dict[str, bool]:
        """
        Get all feature flags and their states
        
        Returns:
            Dictionary mapping feature keys to enabled state
        """
        flags = {}
        
        try:
            # Get all known feature flags
            all_features = set(self.DEFAULT_FEATURE_FLAGS.keys())
            
            # Add any cached flags
            with self._cache_lock:
                all_features.update(self._flag_cache.keys())
            
            # Get current state for each flag
            for feature in all_features:
                try:
                    flags[feature] = self.is_enabled(feature)
                except Exception as e:
                    logger.error(f"Error getting flag {feature}: {str(e)}")
                    flags[feature] = False
            
            return flags
            
        except Exception as e:
            logger.error(f"Error getting all feature flags: {str(e)}")
            return {}
    
    def get_flag_info(self, feature: str) -> Optional[FeatureFlagInfo]:
        """
        Get detailed information about a feature flag
        
        Args:
            feature: Feature flag key
            
        Returns:
            FeatureFlagInfo object or None if not found
        """
        try:
            return self._get_flag_info(feature)
        except FeatureFlagNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error getting flag info for {feature}: {str(e)}")
            return None
    
    def refresh_flags(self) -> bool:
        """
        Refresh all feature flags from configuration service
        
        Returns:
            True if refresh was successful
        """
        try:
            with self._cache_lock:
                # Clear cache to force refresh
                self._flag_cache.clear()
            
            # Refresh configuration service cache
            self.config_service.refresh_config()
            
            # Re-initialize default flags
            self._initialize_default_flags()
            
            logger.info("Feature flags refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing feature flags: {str(e)}")
            return False
    
    def subscribe_to_flag_changes(self, feature: str, callback: Callable[[str, bool, bool], None]) -> str:
        """
        Subscribe to feature flag changes
        
        Args:
            feature: Feature flag key to watch
            callback: Callback function (feature, old_value, new_value)
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        
        with self._subscribers_lock:
            if feature not in self._change_subscribers:
                self._change_subscribers[feature] = {}
            self._change_subscribers[feature][subscription_id] = callback
        
        logger.debug(f"Added feature flag subscription {subscription_id} for {feature}")
        return subscription_id
    
    def unsubscribe_from_flag_changes(self, subscription_id: str) -> bool:
        """
        Remove feature flag change subscription
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed
        """
        with self._subscribers_lock:
            for feature, subscribers in self._change_subscribers.items():
                if subscription_id in subscribers:
                    del subscribers[subscription_id]
                    logger.debug(f"Removed feature flag subscription {subscription_id} for {feature}")
                    return True
        
        return False
    
    def get_usage_metrics(self) -> FeatureFlagUsageMetrics:
        """
        Get feature flag usage metrics
        
        Returns:
            FeatureFlagUsageMetrics object
        """
        with self._metrics_lock:
            return FeatureFlagUsageMetrics(
                total_checks=self._usage_metrics.total_checks,
                enabled_checks=self._usage_metrics.enabled_checks,
                disabled_checks=self._usage_metrics.disabled_checks,
                unique_features_accessed=self._usage_metrics.unique_features_accessed,
                cache_hits=self._usage_metrics.cache_hits,
                cache_misses=self._usage_metrics.cache_misses,
                last_reset=self._usage_metrics.last_reset
            )
    
    def reset_usage_metrics(self) -> None:
        """Reset usage metrics counters"""
        with self._metrics_lock:
            self._usage_metrics = FeatureFlagUsageMetrics(
                last_reset=datetime.now(timezone.utc)
            )
        
        logger.info("Feature flag usage metrics reset")
    
    def get_feature_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all available features with metadata
        
        Returns:
            List of feature information dictionaries
        """
        features = []
        
        try:
            all_flags = self.get_all_flags()
            
            for feature, enabled in all_flags.items():
                flag_info = self.get_flag_info(feature)
                default_info = self.DEFAULT_FEATURE_FLAGS.get(feature, {})
                
                features.append({
                    'key': feature,
                    'enabled': enabled,
                    'description': default_info.get('description', 'No description available'),
                    'default_value': default_info.get('default', False),
                    'last_updated': flag_info.last_updated if flag_info else None,
                    'source': flag_info.source if flag_info else 'default',
                    'usage_count': flag_info.usage_count if flag_info else 0,
                    'last_accessed': flag_info.last_accessed if flag_info else None
                })
            
            return features
            
        except Exception as e:
            logger.error(f"Error getting feature list: {str(e)}")
            return []
    
    def _get_flag_info(self, feature: str) -> FeatureFlagInfo:
        """
        Get feature flag information with caching
        
        Args:
            feature: Feature flag key
            
        Returns:
            FeatureFlagInfo object
            
        Raises:
            FeatureFlagNotFoundError: If feature flag is not found
        """
        # Check cache first
        with self._cache_lock:
            cached_info = self._flag_cache.get(feature)
            if cached_info:
                # Check if cache entry is still valid
                age = (datetime.now(timezone.utc) - cached_info.last_updated).total_seconds()
                if age < self.cache_ttl:
                    # Update access time and usage count
                    cached_info.last_accessed = datetime.now(timezone.utc)
                    cached_info.usage_count += 1
                    
                    if self.metrics_enabled:
                        with self._metrics_lock:
                            self._usage_metrics.cache_hits += 1
                    
                    return cached_info
        
        # Cache miss - get from configuration service
        if self.metrics_enabled:
            with self._metrics_lock:
                self._usage_metrics.cache_misses += 1
        
        try:
            # Get configuration value
            config_value = self.config_service.get_config_with_metadata(feature)
            
            if config_value:
                # Convert to boolean
                enabled = self._convert_to_boolean(config_value.value)
                state = FeatureFlagState.ENABLED if enabled else FeatureFlagState.DISABLED
                source = config_value.source.value
                last_updated = config_value.last_updated
            else:
                # Check if it's a known default flag
                default_info = self.DEFAULT_FEATURE_FLAGS.get(feature)
                if default_info:
                    enabled = default_info['default']
                    state = FeatureFlagState.ENABLED if enabled else FeatureFlagState.DISABLED
                    source = 'default'
                    last_updated = datetime.now(timezone.utc)
                else:
                    raise FeatureFlagNotFoundError(f"Feature flag '{feature}' not found")
            
            # Create flag info
            flag_info = FeatureFlagInfo(
                key=feature,
                enabled=enabled,
                state=state,
                last_updated=last_updated,
                source=source,
                description=self.DEFAULT_FEATURE_FLAGS.get(feature, {}).get('description'),
                usage_count=1,
                last_accessed=datetime.now(timezone.utc)
            )
            
            # Cache the result
            with self._cache_lock:
                self._flag_cache[feature] = flag_info
            
            return flag_info
            
        except FeatureFlagNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting feature flag {feature}: {str(e)}")
            raise FeatureFlagError(f"Failed to get feature flag {feature}: {str(e)}")
    
    def _convert_to_boolean(self, value: Any) -> bool:
        """
        Convert configuration value to boolean
        
        Args:
            value: Value to convert
            
        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
        elif isinstance(value, (int, float)):
            return value != 0
        else:
            return bool(value)
    
    def _initialize_default_flags(self):
        """Initialize cache with default feature flags"""
        try:
            for feature, info in self.DEFAULT_FEATURE_FLAGS.items():
                # Only initialize if not already in cache
                with self._cache_lock:
                    if feature not in self._flag_cache:
                        flag_info = FeatureFlagInfo(
                            key=feature,
                            enabled=info['default'],
                            state=FeatureFlagState.ENABLED if info['default'] else FeatureFlagState.DISABLED,
                            last_updated=datetime.now(timezone.utc),
                            source='default',
                            description=info.get('description'),
                            usage_count=0
                        )
                        self._flag_cache[feature] = flag_info
            
            logger.debug("Initialized default feature flags")
            
        except Exception as e:
            logger.error(f"Error initializing default feature flags: {str(e)}")
    
    def _setup_change_subscriptions(self):
        """Setup subscriptions to configuration changes"""
        try:
            # Subscribe to all configuration changes
            self.event_bus.subscribe(
                EventType.CONFIGURATION_CHANGED,
                '*',  # Match all keys
                self._handle_configuration_change
            )
            
            logger.debug("Setup feature flag change subscriptions")
            
        except Exception as e:
            logger.error(f"Error setting up change subscriptions: {str(e)}")
    
    def _handle_configuration_change(self, event: ConfigurationChangeEvent):
        """
        Handle configuration change events
        
        Args:
            event: Configuration change event
        """
        try:
            feature = event.key
            
            # Check if this is a feature flag
            if not self._is_feature_flag(feature):
                return
            
            # Get old value from cache
            old_enabled = False
            with self._cache_lock:
                cached_info = self._flag_cache.get(feature)
                if cached_info:
                    old_enabled = cached_info.enabled
                    # Remove from cache to force refresh
                    del self._flag_cache[feature]
            
            # Get new value
            new_enabled = self._convert_to_boolean(event.new_value)
            
            # Notify subscribers if value changed
            if old_enabled != new_enabled:
                self._notify_flag_change_subscribers(feature, old_enabled, new_enabled)
            
            logger.info(f"Feature flag {feature} changed from {old_enabled} to {new_enabled}")
            
        except Exception as e:
            logger.error(f"Error handling configuration change for {event.key}: {str(e)}")
    
    def _is_feature_flag(self, key: str) -> bool:
        """
        Check if configuration key is a feature flag
        
        Args:
            key: Configuration key
            
        Returns:
            True if key is a feature flag
        """
        # Check if it's a known default flag
        if key in self.DEFAULT_FEATURE_FLAGS:
            return True
        
        # Check if it starts with common feature flag prefixes
        feature_prefixes = ['enable_', 'disable_', 'feature_', 'flag_']
        return any(key.startswith(prefix) for prefix in feature_prefixes)
    
    def _notify_flag_change_subscribers(self, feature: str, old_value: bool, new_value: bool):
        """
        Notify subscribers of feature flag changes
        
        Args:
            feature: Feature flag key
            old_value: Previous value
            new_value: New value
        """
        with self._subscribers_lock:
            subscribers = self._change_subscribers.get(feature, {})
            
            for subscription_id, callback in subscribers.items():
                try:
                    callback(feature, old_value, new_value)
                except Exception as e:
                    logger.error(f"Error in feature flag change callback {subscription_id}: {str(e)}")
    
    def _update_usage_metrics(self, feature: str, enabled: bool):
        """
        Update usage metrics for feature flag access
        
        Args:
            feature: Feature flag key
            enabled: Whether flag is enabled
        """
        if not self.metrics_enabled:
            return
        
        with self._metrics_lock:
            self._usage_metrics.total_checks += 1
            
            if enabled:
                self._usage_metrics.enabled_checks += 1
            else:
                self._usage_metrics.disabled_checks += 1
            
            # Track unique features (approximate)
            # This is a simple approximation - in production you might want a more accurate method
            if self._usage_metrics.total_checks == 1:
                self._usage_metrics.unique_features_accessed = 1
            else:
                # Estimate based on total checks and cache behavior
                estimated_unique = min(
                    len(self.DEFAULT_FEATURE_FLAGS) + len(self._flag_cache),
                    self._usage_metrics.total_checks
                )
                self._usage_metrics.unique_features_accessed = estimated_unique
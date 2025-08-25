# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Service

Provides high-performance, cached access to system configuration with
environment variable overrides, schema defaults, and change notifications.
"""

import os
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
from cachetools import TTLCache
import uuid

from database import DatabaseManager
from models import SystemConfiguration
from system_configuration_manager import SystemConfigurationManager, ConfigurationSchema

logger = logging.getLogger(__name__)


class ConfigurationSource(Enum):
    """Source of configuration value"""
    ENVIRONMENT = "environment"
    DATABASE = "database"
    DEFAULT = "default"
    CACHE = "cache"


@dataclass
class ConfigurationValue:
    """Configuration value with metadata"""
    key: str
    value: Any
    data_type: str
    source: ConfigurationSource
    requires_restart: bool
    last_updated: datetime
    cached_at: datetime
    ttl: int


class ConfigurationError(Exception):
    """Base configuration error"""
    pass


class ConfigurationNotFoundError(ConfigurationError):
    """Configuration key not found"""
    pass


class ConfigurationValidationError(ConfigurationError):
    """Configuration validation failed"""
    pass


class ConfigurationCacheError(ConfigurationError):
    """Configuration cache error"""
    pass


class ConfigurationServiceUnavailableError(ConfigurationError):
    """Configuration service unavailable"""
    pass


class ConfigurationService:
    """
    High-performance configuration service with caching and event notifications
    
    Features:
    - LRU cache with configurable TTL
    - Environment variable override support
    - Schema default fallback
    - Change event notifications
    - Restart requirement tracking
    """
    
    def __init__(self, db_manager: DatabaseManager, cache_size: int = 1000, 
                 default_ttl: int = 300, environment_prefix: str = "VEDFOLNIR_CONFIG_"):
        """
        Initialize configuration service
        
        Args:
            db_manager: Database manager instance
            cache_size: Maximum cache size (default: 1000)
            default_ttl: Default cache TTL in seconds (default: 300)
            environment_prefix: Environment variable prefix
        """
        self.db_manager = db_manager
        self.system_config_manager = SystemConfigurationManager(db_manager)
        self.environment_prefix = environment_prefix
        self.default_ttl = default_ttl
        
        # Thread-safe cache
        self._cache = TTLCache(maxsize=cache_size, ttl=default_ttl)
        self._cache_lock = threading.RLock()
        
        # Change subscribers
        self._subscribers: Dict[str, Dict[str, Callable]] = {}
        self._subscribers_lock = threading.RLock()
        
        # Restart tracking
        self._pending_restart_configs: set = set()
        self._restart_lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'environment_overrides': 0,
            'database_reads': 0,
            'default_fallbacks': 0,
            'errors': 0
        }
        self._stats_lock = threading.RLock()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with caching and fallback chain
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        try:
            config_value = self.get_config_with_metadata(key)
            return config_value.value if config_value else default
        except ConfigurationNotFoundError:
            return default
        except Exception as e:
            logger.error(f"Error getting configuration {key}: {str(e)}")
            with self._stats_lock:
                self._stats['errors'] += 1
            return default
    
    def get_config_with_metadata(self, key: str) -> Optional[ConfigurationValue]:
        """
        Get configuration value with full metadata
        
        Args:
            key: Configuration key
            
        Returns:
            ConfigurationValue with metadata or None if not found
        """
        try:
            # Check cache first
            with self._cache_lock:
                cached_value = self._cache.get(key)
                if cached_value:
                    with self._stats_lock:
                        self._stats['cache_hits'] += 1
                    cached_value.source = ConfigurationSource.CACHE
                    return cached_value
            
            with self._stats_lock:
                self._stats['cache_misses'] += 1
            
            # Check environment variable override
            env_key = f"{self.environment_prefix}{key.upper()}"
            env_value = os.getenv(env_key)
            
            if env_value is not None:
                with self._stats_lock:
                    self._stats['environment_overrides'] += 1
                
                # Get schema for type conversion
                schema = self.system_config_manager.get_configuration_schema(key)
                data_type = schema.data_type.value if schema else 'string'
                
                try:
                    typed_value = self._convert_value(env_value, data_type)
                except (ValueError, TypeError):
                    typed_value = env_value
                
                config_value = ConfigurationValue(
                    key=key,
                    value=typed_value,
                    data_type=data_type,
                    source=ConfigurationSource.ENVIRONMENT,
                    requires_restart=schema.requires_restart if schema else False,
                    last_updated=datetime.now(timezone.utc),
                    cached_at=datetime.now(timezone.utc),
                    ttl=self.default_ttl
                )
                
                # Cache the value
                with self._cache_lock:
                    self._cache[key] = config_value
                
                return config_value
            
            # Get from database
            with self._stats_lock:
                self._stats['database_reads'] += 1
            
            try:
                with self.db_manager.get_session() as session:
                    db_config = session.query(SystemConfiguration).filter_by(key=key).first()
                    
                    if db_config:
                        config_value = ConfigurationValue(
                            key=key,
                            value=db_config.get_typed_value(),
                            data_type=db_config.data_type,
                            source=ConfigurationSource.DATABASE,
                            requires_restart=self._requires_restart(key),
                            last_updated=db_config.updated_at,
                            cached_at=datetime.now(timezone.utc),
                            ttl=self.default_ttl
                        )
                        
                        # Cache the value
                        with self._cache_lock:
                            self._cache[key] = config_value
                        
                        return config_value
            
            except Exception as e:
                logger.error(f"Database error getting configuration {key}: {str(e)}")
                # Continue to schema default fallback
            
            # Fall back to schema default
            schema = self.system_config_manager.get_configuration_schema(key)
            if schema and schema.default_value is not None:
                with self._stats_lock:
                    self._stats['default_fallbacks'] += 1
                
                config_value = ConfigurationValue(
                    key=key,
                    value=schema.default_value,
                    data_type=schema.data_type.value,
                    source=ConfigurationSource.DEFAULT,
                    requires_restart=schema.requires_restart,
                    last_updated=datetime.now(timezone.utc),
                    cached_at=datetime.now(timezone.utc),
                    ttl=self.default_ttl
                )
                
                # Cache the value
                with self._cache_lock:
                    self._cache[key] = config_value
                
                return config_value
            
            # Configuration not found
            raise ConfigurationNotFoundError(f"Configuration key '{key}' not found")
            
        except ConfigurationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting configuration {key}: {str(e)}")
            with self._stats_lock:
                self._stats['errors'] += 1
            raise ConfigurationError(f"Failed to get configuration {key}: {str(e)}")
    
    def refresh_config(self, key: str = None) -> bool:
        """
        Refresh configuration cache
        
        Args:
            key: Specific key to refresh, or None for all
            
        Returns:
            True if successful
        """
        try:
            with self._cache_lock:
                if key:
                    # Refresh specific key
                    if key in self._cache:
                        del self._cache[key]
                    logger.info(f"Refreshed configuration cache for key: {key}")
                else:
                    # Refresh all
                    self._cache.clear()
                    logger.info("Refreshed entire configuration cache")
            
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing configuration cache: {str(e)}")
            return False
    
    def is_restart_required(self) -> bool:
        """
        Check if any pending configuration changes require restart
        
        Returns:
            True if restart is required
        """
        with self._restart_lock:
            return len(self._pending_restart_configs) > 0
    
    def get_pending_restart_configs(self) -> List[str]:
        """
        Get list of configuration keys requiring restart
        
        Returns:
            List of configuration keys
        """
        with self._restart_lock:
            return list(self._pending_restart_configs)
    
    def subscribe_to_changes(self, key: str, callback: Callable[[str, Any, Any], None]) -> str:
        """
        Subscribe to configuration changes
        
        Args:
            key: Configuration key to watch
            callback: Callback function (key, old_value, new_value)
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        
        with self._subscribers_lock:
            if key not in self._subscribers:
                self._subscribers[key] = {}
            self._subscribers[key][subscription_id] = callback
        
        logger.debug(f"Added subscription {subscription_id} for key {key}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove subscription
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed
        """
        with self._subscribers_lock:
            for key, subscribers in self._subscribers.items():
                if subscription_id in subscribers:
                    del subscribers[subscription_id]
                    logger.debug(f"Removed subscription {subscription_id} for key {key}")
                    return True
        
        return False
    
    def notify_change(self, key: str, old_value: Any, new_value: Any):
        """
        Notify subscribers of configuration change
        
        Args:
            key: Configuration key that changed
            old_value: Previous value
            new_value: New value
        """
        # Invalidate cache
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
        
        # Track restart requirement
        if self._requires_restart(key):
            with self._restart_lock:
                self._pending_restart_configs.add(key)
        
        # Notify subscribers
        with self._subscribers_lock:
            subscribers = self._subscribers.get(key, {})
            for subscription_id, callback in subscribers.items():
                try:
                    callback(key, old_value, new_value)
                except Exception as e:
                    logger.error(f"Error in subscription callback {subscription_id}: {str(e)}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache and service statistics
        
        Returns:
            Dictionary with statistics
        """
        with self._cache_lock:
            cache_info = {
                'size': len(self._cache),
                'maxsize': self._cache.maxsize,
                'ttl': self._cache.ttl,
                'currsize': len(self._cache)
            }
        
        with self._stats_lock:
            stats = self._stats.copy()
        
        # Calculate hit rate
        total_requests = stats['cache_hits'] + stats['cache_misses']
        hit_rate = stats['cache_hits'] / total_requests if total_requests > 0 else 0.0
        
        return {
            'cache': cache_info,
            'statistics': stats,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }
    
    def _convert_value(self, value: str, data_type: str) -> Any:
        """
        Convert string value to appropriate type
        
        Args:
            value: String value to convert
            data_type: Target data type
            
        Returns:
            Converted value
        """
        if data_type == 'integer':
            return int(value)
        elif data_type == 'float':
            return float(value)
        elif data_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif data_type == 'json':
            return json.loads(value)
        else:
            return value
    
    def _requires_restart(self, key: str) -> bool:
        """
        Check if configuration key requires restart
        
        Args:
            key: Configuration key
            
        Returns:
            True if restart is required
        """
        schema = self.system_config_manager.get_configuration_schema(key)
        return schema.requires_restart if schema else False
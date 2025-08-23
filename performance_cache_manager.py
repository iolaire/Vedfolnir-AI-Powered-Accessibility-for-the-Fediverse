# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Cache Manager for Multi-Tenant Caption Management

This module provides Redis-based caching for frequently accessed data to improve
response times for admin dashboard operations, job status queries, user permissions,
and system metrics.
"""

import json
import redis
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from functools import wraps
from threading import Lock

from database import DatabaseManager
from models import User, UserRole, CaptionGenerationTask, TaskStatus
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """Cache configuration settings"""
    admin_dashboard_ttl: int = 300  # 5 minutes
    job_status_ttl: int = 60  # 1 minute
    user_permissions_ttl: int = 1800  # 30 minutes
    system_metrics_ttl: int = 120  # 2 minutes
    default_ttl: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay: float = 0.1

class CacheKeyGenerator:
    """Generates consistent cache keys for different data types"""
    
    PREFIX = "vedfolnir:cache:"
    
    @staticmethod
    def admin_dashboard(admin_user_id: int) -> str:
        """Generate cache key for admin dashboard data"""
        return f"{CacheKeyGenerator.PREFIX}admin_dashboard:{admin_user_id}"
    
    @staticmethod
    def job_status(task_id: str) -> str:
        """Generate cache key for job status"""
        return f"{CacheKeyGenerator.PREFIX}job_status:{task_id}"
    
    @staticmethod
    def user_permissions(user_id: int) -> str:
        """Generate cache key for user permissions"""
        return f"{CacheKeyGenerator.PREFIX}user_permissions:{user_id}"
    
    @staticmethod
    def system_metrics() -> str:
        """Generate cache key for system metrics"""
        return f"{CacheKeyGenerator.PREFIX}system_metrics"
    
    @staticmethod
    def user_job_list(user_id: int) -> str:
        """Generate cache key for user job list"""
        return f"{CacheKeyGenerator.PREFIX}user_jobs:{user_id}"
    
    @staticmethod
    def queue_stats() -> str:
        """Generate cache key for queue statistics"""
        return f"{CacheKeyGenerator.PREFIX}queue_stats"
    
    @staticmethod
    def performance_metrics() -> str:
        """Generate cache key for performance metrics"""
        return f"{CacheKeyGenerator.PREFIX}performance_metrics"

class PerformanceCacheManager:
    """Redis-based cache manager for performance optimization"""
    
    def __init__(self, redis_client: redis.Redis, db_manager: DatabaseManager, 
                 config: Optional[CacheConfig] = None):
        """
        Initialize performance cache manager
        
        Args:
            redis_client: Redis client instance
            db_manager: Database manager for fallback queries
            config: Cache configuration settings
        """
        self.redis_client = redis_client
        self.db_manager = db_manager
        self.config = config or CacheConfig()
        self._lock = Lock()
        
        # Test Redis connection
        try:
            self.redis_client.ping()
            logger.info("Performance cache manager initialized with Redis backend")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for caching: {e}")
            raise
    
    def _serialize_data(self, data: Any) -> str:
        """Serialize data for Redis storage"""
        try:
            if hasattr(data, 'to_dict'):
                return json.dumps(data.to_dict())
            elif hasattr(data, '__dict__'):
                return json.dumps(asdict(data))
            else:
                return json.dumps(data, default=str)
        except Exception as e:
            logger.error(f"Error serializing data for cache: {e}")
            return json.dumps({'error': 'serialization_failed'})
    
    def _deserialize_data(self, data: str) -> Any:
        """Deserialize data from Redis storage"""
        try:
            return json.loads(data)
        except Exception as e:
            logger.error(f"Error deserializing data from cache: {e}")
            return None
    
    def set_cache(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """
        Set data in cache with optional TTL
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            serialized_data = self._serialize_data(data)
            ttl = ttl or self.config.default_ttl
            
            # Add metadata
            cache_entry = {
                'data': json.loads(serialized_data) if serialized_data != '{"error": "serialization_failed"}' else serialized_data,
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'ttl': ttl
            }
            
            result = self.redis_client.setex(
                key, 
                ttl, 
                json.dumps(cache_entry, default=str)
            )
            
            if result:
                logger.debug(f"Cached data with key: {key[:50]}...")
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {e}")
            return False
    
    def get_cache(self, key: str) -> Optional[Any]:
        """
        Get data from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        try:
            cached_data = self.redis_client.get(key)
            if not cached_data:
                return None
            
            cache_entry = json.loads(cached_data)
            
            # Check if we have the expected structure
            if isinstance(cache_entry, dict) and 'data' in cache_entry:
                logger.debug(f"Cache hit for key: {key[:50]}...")
                return cache_entry['data']
            else:
                # Legacy format or direct data
                return cache_entry
                
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {e}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """
        Delete data from cache
        
        Args:
            key: Cache key to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.redis_client.delete(key)
            if result:
                logger.debug(f"Deleted cache key: {key[:50]}...")
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting cache for key {key}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern
        
        Args:
            pattern: Redis key pattern (e.g., "vedfolnir:cache:user_*")
            
        Returns:
            int: Number of keys deleted
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0
    
    def cache_admin_dashboard_data(self, admin_user_id: int, dashboard_data: Dict[str, Any]) -> bool:
        """
        Cache admin dashboard data
        
        Args:
            admin_user_id: Admin user ID
            dashboard_data: Dashboard data to cache
            
        Returns:
            bool: True if successful
        """
        key = CacheKeyGenerator.admin_dashboard(admin_user_id)
        return self.set_cache(key, dashboard_data, self.config.admin_dashboard_ttl)
    
    def get_admin_dashboard_data(self, admin_user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached admin dashboard data
        
        Args:
            admin_user_id: Admin user ID
            
        Returns:
            Cached dashboard data or None
        """
        key = CacheKeyGenerator.admin_dashboard(admin_user_id)
        return self.get_cache(key)
    
    def cache_job_status(self, task_id: str, status_data: Dict[str, Any]) -> bool:
        """
        Cache job status data
        
        Args:
            task_id: Task ID
            status_data: Job status data to cache
            
        Returns:
            bool: True if successful
        """
        key = CacheKeyGenerator.job_status(task_id)
        return self.set_cache(key, status_data, self.config.job_status_ttl)
    
    def get_job_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached job status data
        
        Args:
            task_id: Task ID
            
        Returns:
            Cached job status or None
        """
        key = CacheKeyGenerator.job_status(task_id)
        return self.get_cache(key)
    
    def cache_user_permissions(self, user_id: int, permissions_data: Dict[str, Any]) -> bool:
        """
        Cache user permissions and role data
        
        Args:
            user_id: User ID
            permissions_data: User permissions data to cache
            
        Returns:
            bool: True if successful
        """
        key = CacheKeyGenerator.user_permissions(user_id)
        return self.set_cache(key, permissions_data, self.config.user_permissions_ttl)
    
    def get_user_permissions(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached user permissions data
        
        Args:
            user_id: User ID
            
        Returns:
            Cached permissions data or None
        """
        key = CacheKeyGenerator.user_permissions(user_id)
        return self.get_cache(key)
    
    def cache_system_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """
        Cache system metrics data
        
        Args:
            metrics_data: System metrics to cache
            
        Returns:
            bool: True if successful
        """
        key = CacheKeyGenerator.system_metrics()
        return self.set_cache(key, metrics_data, self.config.system_metrics_ttl)
    
    def get_system_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get cached system metrics data
        
        Returns:
            Cached system metrics or None
        """
        key = CacheKeyGenerator.system_metrics()
        return self.get_cache(key)
    
    def invalidate_user_caches(self, user_id: int) -> int:
        """
        Invalidate all caches related to a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            int: Number of cache keys invalidated
        """
        patterns = [
            f"{CacheKeyGenerator.PREFIX}user_permissions:{user_id}",
            f"{CacheKeyGenerator.PREFIX}user_jobs:{user_id}",
            f"{CacheKeyGenerator.PREFIX}admin_dashboard:{user_id}"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.invalidate_pattern(pattern)
        
        return total_deleted
    
    def invalidate_job_caches(self, task_id: str) -> int:
        """
        Invalidate all caches related to a specific job
        
        Args:
            task_id: Task ID
            
        Returns:
            int: Number of cache keys invalidated
        """
        patterns = [
            f"{CacheKeyGenerator.PREFIX}job_status:{task_id}",
            f"{CacheKeyGenerator.PREFIX}queue_stats",
            f"{CacheKeyGenerator.PREFIX}system_metrics",
            f"{CacheKeyGenerator.PREFIX}performance_metrics"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.invalidate_pattern(pattern)
        
        return total_deleted
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            redis_info = self.redis_client.info()
            
            # Get cache-specific keys
            cache_keys = self.redis_client.keys(f"{CacheKeyGenerator.PREFIX}*")
            
            return {
                'total_cache_keys': len(cache_keys),
                'redis_memory_used': redis_info.get('used_memory_human', '0B'),
                'redis_keyspace_hits': redis_info.get('keyspace_hits', 0),
                'redis_keyspace_misses': redis_info.get('keyspace_misses', 0),
                'cache_hit_rate': self._calculate_hit_rate(redis_info),
                'connected_clients': redis_info.get('connected_clients', 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def _calculate_hit_rate(self, redis_info: Dict[str, Any]) -> float:
        """Calculate cache hit rate percentage"""
        hits = redis_info.get('keyspace_hits', 0)
        misses = redis_info.get('keyspace_misses', 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return round((hits / total) * 100, 2)

def cached_method(cache_manager_attr: str = 'cache_manager', 
                 key_generator: Callable = None,
                 ttl: Optional[int] = None,
                 invalidate_on_error: bool = True):
    """
    Decorator for caching method results
    
    Args:
        cache_manager_attr: Attribute name of the cache manager on the class
        key_generator: Function to generate cache key from method args
        ttl: Time to live for cached data
        invalidate_on_error: Whether to invalidate cache on method error
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get cache manager from the instance
            cache_manager = getattr(self, cache_manager_attr, None)
            if not cache_manager:
                # No cache manager, execute method directly
                return func(self, *args, **kwargs)
            
            # Generate cache key
            if key_generator:
                cache_key = key_generator(self, *args, **kwargs)
            else:
                # Default key generation
                method_name = func.__name__
                args_str = '_'.join(str(arg) for arg in args)
                cache_key = f"{CacheKeyGenerator.PREFIX}{method_name}:{args_str}"
            
            # Try to get from cache first
            cached_result = cache_manager.get_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for method {func.__name__}")
                return cached_result
            
            # Execute method and cache result
            try:
                result = func(self, *args, **kwargs)
                cache_manager.set_cache(cache_key, result, ttl)
                logger.debug(f"Cached result for method {func.__name__}")
                return result
            except Exception as e:
                if invalidate_on_error:
                    cache_manager.delete_cache(cache_key)
                raise
        
        return wrapper
    return decorator
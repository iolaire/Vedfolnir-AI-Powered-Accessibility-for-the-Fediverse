# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Cache

High-performance, thread-safe caching layer for configuration values
with per-key TTL support and comprehensive statistics collection.
"""

import time
import threading
import logging
from typing import Any, Dict, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timezone
from cachetools import TTLCache
import psutil
import os

if TYPE_CHECKING:
    from app.core.configuration.core.configuration_service import ConfigurationValue

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics and performance metrics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_keys: int = 0
    memory_usage_bytes: int = 0
    hit_rate: float = 0.0
    average_access_time_ms: float = 0.0
    last_cleanup: Optional[datetime] = None
    cache_efficiency: float = 0.0


@dataclass
class CacheEntry:
    """Cache entry with per-key TTL and metadata"""
    value: 'ConfigurationValue'
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if entry is expired based on TTL"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """Update access metadata"""
        self.last_accessed = time.time()
        self.access_count += 1


class ConfigurationCache:
    """
    High-performance configuration cache with advanced features
    
    Features:
    - Thread-safe LRU cache operations
    - Per-key TTL support
    - Cache statistics and performance monitoring
    - Memory usage tracking
    - Intelligent cache invalidation
    - Cache efficiency optimization
    """
    
    def __init__(self, maxsize: int = 1000, default_ttl: int = 300, 
                 cleanup_interval: int = 60, memory_limit_mb: int = 100):
        """
        Initialize configuration cache
        
        Args:
            maxsize: Maximum number of cache entries
            default_ttl: Default TTL in seconds
            cleanup_interval: Cleanup interval in seconds
            memory_limit_mb: Memory limit in MB
        """
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        
        # Thread-safe cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_lock = threading.RLock()
        
        # Statistics tracking
        self._stats = CacheStats()
        self._stats_lock = threading.RLock()
        
        # Performance tracking
        self._access_times: list = []
        self._access_times_lock = threading.RLock()
        
        # Cleanup tracking
        self._last_cleanup = time.time()
        self._cleanup_lock = threading.RLock()
        
        # Start background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional['ConfigurationValue']:
        """
        Get configuration value from cache
        
        Args:
            key: Configuration key
            
        Returns:
            ConfigurationValue or None if not found/expired
        """
        start_time = time.time()
        
        try:
            with self._cache_lock:
                entry = self._cache.get(key)
                
                if entry is None:
                    # Cache miss
                    with self._stats_lock:
                        self._stats.misses += 1
                    self._record_access_time(start_time)
                    return None
                
                # Check if expired
                if entry.is_expired():
                    # Remove expired entry
                    del self._cache[key]
                    with self._stats_lock:
                        self._stats.misses += 1
                        self._stats.evictions += 1
                    self._record_access_time(start_time)
                    return None
                
                # Cache hit
                entry.touch()
                with self._stats_lock:
                    self._stats.hits += 1
                
                self._record_access_time(start_time)
                return entry.value
                
        except Exception as e:
            logger.error(f"Error getting cache entry for key {key}: {str(e)}")
            with self._stats_lock:
                self._stats.misses += 1
            self._record_access_time(start_time)
            return None
    
    def set(self, key: str, value: 'ConfigurationValue', ttl: int = None) -> None:
        """
        Set configuration value in cache
        
        Args:
            key: Configuration key
            value: Configuration value
            ttl: Time to live in seconds (None for default)
        """
        try:
            effective_ttl = ttl if ttl is not None else self.default_ttl
            
            with self._cache_lock:
                # Check memory limit before adding
                if self._should_evict_for_memory():
                    self._evict_lru_entries(1)
                
                # Check size limit
                if len(self._cache) >= self.maxsize and key not in self._cache:
                    self._evict_lru_entries(1)
                
                # Create cache entry
                entry = CacheEntry(
                    value=value,
                    ttl=effective_ttl
                )
                
                self._cache[key] = entry
                
                # Update statistics
                with self._stats_lock:
                    self._stats.total_keys = len(self._cache)
                    self._stats.memory_usage_bytes = self._estimate_memory_usage()
                
        except Exception as e:
            logger.error(f"Error setting cache entry for key {key}: {str(e)}")
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate specific cache entry
        
        Args:
            key: Configuration key to invalidate
            
        Returns:
            True if key was found and removed
        """
        try:
            with self._cache_lock:
                if key in self._cache:
                    del self._cache[key]
                    with self._stats_lock:
                        self._stats.total_keys = len(self._cache)
                        self._stats.evictions += 1
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error invalidating cache entry for key {key}: {str(e)}")
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        try:
            with self._cache_lock:
                evicted_count = len(self._cache)
                self._cache.clear()
                
                with self._stats_lock:
                    self._stats.total_keys = 0
                    self._stats.memory_usage_bytes = 0
                    self._stats.evictions += evicted_count
                
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
    
    def get_stats(self) -> CacheStats:
        """
        Get comprehensive cache statistics
        
        Returns:
            CacheStats object with current statistics
        """
        with self._stats_lock:
            stats = CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                total_keys=len(self._cache),
                memory_usage_bytes=self._estimate_memory_usage(),
                hit_rate=self._calculate_hit_rate(),
                average_access_time_ms=self._calculate_average_access_time(),
                last_cleanup=self._stats.last_cleanup,
                cache_efficiency=self._calculate_cache_efficiency()
            )
        
        return stats
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information
        
        Returns:
            Dictionary with cache details
        """
        with self._cache_lock:
            entries_info = []
            for key, entry in self._cache.items():
                entries_info.append({
                    'key': key,
                    'created_at': datetime.fromtimestamp(entry.created_at, timezone.utc),
                    'last_accessed': datetime.fromtimestamp(entry.last_accessed, timezone.utc),
                    'access_count': entry.access_count,
                    'ttl': entry.ttl,
                    'is_expired': entry.is_expired(),
                    'age_seconds': time.time() - entry.created_at
                })
            
            return {
                'maxsize': self.maxsize,
                'current_size': len(self._cache),
                'default_ttl': self.default_ttl,
                'memory_limit_bytes': self.memory_limit_bytes,
                'entries': entries_info,
                'stats': self.get_stats()
            }
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries
        
        Returns:
            Number of entries removed
        """
        removed_count = 0
        
        try:
            with self._cache_lock:
                expired_keys = []
                
                for key, entry in self._cache.items():
                    if entry.is_expired():
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self._cache[key]
                    removed_count += 1
                
                if removed_count > 0:
                    with self._stats_lock:
                        self._stats.total_keys = len(self._cache)
                        self._stats.evictions += removed_count
                        self._stats.last_cleanup = datetime.now(timezone.utc)
                
        except Exception as e:
            logger.error(f"Error during cache cleanup: {str(e)}")
        
        return removed_count
    
    def optimize_cache(self) -> Dict[str, int]:
        """
        Optimize cache by removing least useful entries
        
        Returns:
            Dictionary with optimization results
        """
        results = {
            'expired_removed': 0,
            'lru_removed': 0,
            'memory_freed_bytes': 0
        }
        
        try:
            # Remove expired entries
            results['expired_removed'] = self.cleanup_expired()
            
            # Check memory usage
            if self._should_evict_for_memory():
                memory_before = self._estimate_memory_usage()
                entries_to_remove = max(1, len(self._cache) // 10)  # Remove 10%
                results['lru_removed'] = self._evict_lru_entries(entries_to_remove)
                memory_after = self._estimate_memory_usage()
                results['memory_freed_bytes'] = memory_before - memory_after
            
        except Exception as e:
            logger.error(f"Error during cache optimization: {str(e)}")
        
        return results
    
    def _background_cleanup(self):
        """Background thread for periodic cache cleanup"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                
                with self._cleanup_lock:
                    if time.time() - self._last_cleanup >= self.cleanup_interval:
                        removed = self.cleanup_expired()
                        if removed > 0:
                            logger.debug(f"Background cleanup removed {removed} expired entries")
                        self._last_cleanup = time.time()
                
            except Exception as e:
                logger.error(f"Error in background cleanup: {str(e)}")
    
    def _should_evict_for_memory(self) -> bool:
        """Check if cache should evict entries due to memory pressure"""
        try:
            current_memory = self._estimate_memory_usage()
            return current_memory > self.memory_limit_bytes
        except Exception:
            return False
    
    def _evict_lru_entries(self, count: int) -> int:
        """
        Evict least recently used entries
        
        Args:
            count: Number of entries to evict
            
        Returns:
            Number of entries actually evicted
        """
        evicted = 0
        
        try:
            with self._cache_lock:
                if len(self._cache) == 0:
                    return 0
                
                # Sort by last accessed time (LRU first)
                sorted_entries = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].last_accessed
                )
                
                # Remove oldest entries
                for key, _ in sorted_entries[:count]:
                    if key in self._cache:
                        del self._cache[key]
                        evicted += 1
                
                if evicted > 0:
                    with self._stats_lock:
                        self._stats.total_keys = len(self._cache)
                        self._stats.evictions += evicted
                
        except Exception as e:
            logger.error(f"Error evicting LRU entries: {str(e)}")
        
        return evicted
    
    def _estimate_memory_usage(self) -> int:
        """
        Estimate memory usage of cache
        
        Returns:
            Estimated memory usage in bytes
        """
        try:
            # Simple estimation based on entry count and average size
            if len(self._cache) == 0:
                return 0
            
            # Estimate average entry size (key + value + metadata)
            avg_key_size = 50  # Average key length
            avg_value_size = 200  # Average serialized value size
            metadata_size = 100  # Entry metadata overhead
            
            estimated_size = len(self._cache) * (avg_key_size + avg_value_size + metadata_size)
            return estimated_size
            
        except Exception:
            return 0
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_requests = self._stats.hits + self._stats.misses
        if total_requests == 0:
            return 0.0
        return self._stats.hits / total_requests
    
    def _calculate_average_access_time(self) -> float:
        """Calculate average access time in milliseconds"""
        with self._access_times_lock:
            if not self._access_times:
                return 0.0
            return sum(self._access_times) / len(self._access_times) * 1000
    
    def _calculate_cache_efficiency(self) -> float:
        """
        Calculate cache efficiency score (0.0 to 1.0)
        
        Considers hit rate, memory usage, and access patterns
        """
        hit_rate = self._calculate_hit_rate()
        
        # Memory efficiency (lower usage is better)
        memory_efficiency = 1.0
        if self.memory_limit_bytes > 0:
            memory_usage_ratio = self._stats.memory_usage_bytes / self.memory_limit_bytes
            memory_efficiency = max(0.0, 1.0 - memory_usage_ratio)
        
        # Size efficiency (not too full, not too empty)
        size_ratio = len(self._cache) / self.maxsize if self.maxsize > 0 else 0
        size_efficiency = 1.0 - abs(0.7 - size_ratio)  # Optimal around 70% full
        size_efficiency = max(0.0, min(1.0, size_efficiency))
        
        # Weighted average
        efficiency = (hit_rate * 0.5) + (memory_efficiency * 0.3) + (size_efficiency * 0.2)
        return min(1.0, max(0.0, efficiency))
    
    def _record_access_time(self, start_time: float):
        """Record access time for performance monitoring"""
        access_time = time.time() - start_time
        
        with self._access_times_lock:
            self._access_times.append(access_time)
            
            # Keep only recent access times (last 1000)
            if len(self._access_times) > 1000:
                self._access_times = self._access_times[-1000:]
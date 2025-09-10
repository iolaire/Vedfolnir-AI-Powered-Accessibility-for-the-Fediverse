# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for ConfigurationCache
"""

import unittest
import os
import sys
import time
import threading
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.configuration.cache.configuration_cache import ConfigurationCache, CacheEntry, CacheStats
from app.core.configuration.core.configuration_service import ConfigurationValue, ConfigurationSource


class TestConfigurationCache(unittest.TestCase):
    """Test cases for ConfigurationCache"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create cache with small limits for testing
        self.cache = ConfigurationCache(
            maxsize=5,
            default_ttl=1,  # Short TTL for testing
            cleanup_interval=0.5,  # Fast cleanup for testing
            memory_limit_mb=1  # Small memory limit
        )
        
        # Sample configuration value
        self.sample_config = ConfigurationValue(
            key="test_key",
            value="test_value",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
    
    def tearDown(self):
        """Clean up after tests"""
        self.cache.clear()
    
    def test_cache_entry_creation(self):
        """Test CacheEntry creation and methods"""
        entry = CacheEntry(value=self.sample_config, ttl=60)
        
        # Test initial state
        self.assertEqual(entry.value, self.sample_config)
        self.assertEqual(entry.access_count, 0)
        self.assertEqual(entry.ttl, 60)
        self.assertFalse(entry.is_expired())
        
        # Test touch method
        initial_access_time = entry.last_accessed
        time.sleep(0.01)  # Small delay
        entry.touch()
        
        self.assertEqual(entry.access_count, 1)
        self.assertGreater(entry.last_accessed, initial_access_time)
    
    def test_cache_entry_expiration(self):
        """Test cache entry TTL expiration"""
        # Create entry with very short TTL
        entry = CacheEntry(value=self.sample_config, ttl=0.1)
        
        # Should not be expired initially
        self.assertFalse(entry.is_expired())
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired now
        self.assertTrue(entry.is_expired())
        
        # Test entry with no TTL (never expires)
        entry_no_ttl = CacheEntry(value=self.sample_config, ttl=None)
        self.assertFalse(entry_no_ttl.is_expired())
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        # Set value in cache
        self.cache.set("test_key", self.sample_config)
        
        # Get value from cache
        result = self.cache.get("test_key")
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.key, "test_key")
        self.assertEqual(result.value, "test_value")
        
        # Verify statistics
        stats = self.cache.get_stats()
        self.assertEqual(stats.hits, 1)
        self.assertEqual(stats.misses, 0)
        self.assertEqual(stats.total_keys, 1)
    
    def test_cache_miss(self):
        """Test cache miss for non-existent key"""
        result = self.cache.get("nonexistent_key")
        
        # Should return None
        self.assertIsNone(result)
        
        # Verify statistics
        stats = self.cache.get_stats()
        self.assertEqual(stats.hits, 0)
        self.assertEqual(stats.misses, 1)
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        # Set value with short TTL
        self.cache.set("test_key", self.sample_config, ttl=0.1)
        
        # Should be available immediately
        result = self.cache.get("test_key")
        self.assertIsNotNone(result)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired and return None
        result = self.cache.get("test_key")
        self.assertIsNone(result)
        
        # Verify statistics show eviction
        stats = self.cache.get_stats()
        self.assertEqual(stats.evictions, 1)
    
    def test_cache_size_limit(self):
        """Test cache size limit enforcement"""
        # Fill cache to capacity
        for i in range(5):
            config = ConfigurationValue(
                key=f"key_{i}",
                value=f"value_{i}",
                data_type="string",
                source=ConfigurationSource.DATABASE,
                requires_restart=False,
                last_updated=datetime.now(timezone.utc),
                cached_at=datetime.now(timezone.utc),
                ttl=300
            )
            self.cache.set(f"key_{i}", config)
        
        # Verify cache is at capacity
        stats = self.cache.get_stats()
        self.assertEqual(stats.total_keys, 5)
        
        # Add one more item (should evict LRU)
        extra_config = ConfigurationValue(
            key="extra_key",
            value="extra_value",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        self.cache.set("extra_key", extra_config)
        
        # Should still be at capacity
        stats = self.cache.get_stats()
        self.assertEqual(stats.total_keys, 5)
        self.assertGreater(stats.evictions, 0)
    
    def test_cache_invalidation(self):
        """Test cache entry invalidation"""
        # Set value in cache
        self.cache.set("test_key", self.sample_config)
        
        # Verify it's there
        result = self.cache.get("test_key")
        self.assertIsNotNone(result)
        
        # Invalidate the key
        success = self.cache.invalidate("test_key")
        self.assertTrue(success)
        
        # Should no longer be in cache
        result = self.cache.get("test_key")
        self.assertIsNone(result)
        
        # Try to invalidate non-existent key
        success = self.cache.invalidate("nonexistent_key")
        self.assertFalse(success)
    
    def test_cache_clear(self):
        """Test cache clear operation"""
        # Add multiple items
        for i in range(3):
            config = ConfigurationValue(
                key=f"key_{i}",
                value=f"value_{i}",
                data_type="string",
                source=ConfigurationSource.DATABASE,
                requires_restart=False,
                last_updated=datetime.now(timezone.utc),
                cached_at=datetime.now(timezone.utc),
                ttl=300
            )
            self.cache.set(f"key_{i}", config)
        
        # Verify items are there
        stats = self.cache.get_stats()
        self.assertEqual(stats.total_keys, 3)
        
        # Clear cache
        self.cache.clear()
        
        # Verify cache is empty
        stats = self.cache.get_stats()
        self.assertEqual(stats.total_keys, 0)
        self.assertEqual(stats.memory_usage_bytes, 0)
    
    def test_cache_statistics(self):
        """Test cache statistics collection"""
        # Perform various operations
        self.cache.set("key1", self.sample_config)
        self.cache.get("key1")  # Hit
        self.cache.get("key1")  # Another hit
        self.cache.get("nonexistent")  # Miss
        
        # Get statistics
        stats = self.cache.get_stats()
        
        # Verify statistics
        self.assertEqual(stats.hits, 2)
        self.assertEqual(stats.misses, 1)
        self.assertEqual(stats.total_keys, 1)
        self.assertGreater(stats.hit_rate, 0.5)  # 2/3 = 0.67
        self.assertGreaterEqual(stats.average_access_time_ms, 0)
        self.assertGreaterEqual(stats.cache_efficiency, 0)
        self.assertLessEqual(stats.cache_efficiency, 1)
    
    def test_cache_info(self):
        """Test detailed cache information"""
        # Add some entries
        self.cache.set("key1", self.sample_config)
        self.cache.set("key2", self.sample_config, ttl=60)
        
        # Get cache info
        info = self.cache.get_cache_info()
        
        # Verify structure
        self.assertIn('maxsize', info)
        self.assertIn('current_size', info)
        self.assertIn('entries', info)
        self.assertIn('stats', info)
        
        # Verify entries info
        self.assertEqual(len(info['entries']), 2)
        
        entry_keys = [entry['key'] for entry in info['entries']]
        self.assertIn('key1', entry_keys)
        self.assertIn('key2', entry_keys)
        
        # Verify entry details
        for entry in info['entries']:
            self.assertIn('created_at', entry)
            self.assertIn('last_accessed', entry)
            self.assertIn('access_count', entry)
            self.assertIn('ttl', entry)
            self.assertIn('is_expired', entry)
            self.assertIn('age_seconds', entry)
    
    def test_cleanup_expired(self):
        """Test expired entry cleanup"""
        # Add entries with different TTLs
        self.cache.set("short_ttl", self.sample_config, ttl=0.1)
        self.cache.set("long_ttl", self.sample_config, ttl=60)
        
        # Verify both are there
        self.assertEqual(len(self.cache._cache), 2)
        
        # Wait for short TTL to expire
        time.sleep(0.2)
        
        # Run cleanup
        removed_count = self.cache.cleanup_expired()
        
        # Should have removed one entry
        self.assertEqual(removed_count, 1)
        self.assertEqual(len(self.cache._cache), 1)
        
        # Verify the right entry remains
        result = self.cache.get("long_ttl")
        self.assertIsNotNone(result)
        
        result = self.cache.get("short_ttl")
        self.assertIsNone(result)
    
    def test_cache_optimization(self):
        """Test cache optimization"""
        # Add entries with different TTLs
        self.cache.set("expired1", self.sample_config, ttl=0.1)
        self.cache.set("expired2", self.sample_config, ttl=0.1)
        self.cache.set("valid", self.sample_config, ttl=60)
        
        # Wait for some to expire
        time.sleep(0.2)
        
        # Run optimization
        results = self.cache.optimize_cache()
        
        # Verify results structure
        self.assertIn('expired_removed', results)
        self.assertIn('lru_removed', results)
        self.assertIn('memory_freed_bytes', results)
        
        # Should have removed expired entries
        self.assertGreaterEqual(results['expired_removed'], 2)
    
    def test_thread_safety(self):
        """Test thread safety of cache operations"""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    key = f"worker_{worker_id}_key_{i}"
                    config = ConfigurationValue(
                        key=key,
                        value=f"value_{i}",
                        data_type="string",
                        source=ConfigurationSource.DATABASE,
                        requires_restart=False,
                        last_updated=datetime.now(timezone.utc),
                        cached_at=datetime.now(timezone.utc),
                        ttl=300
                    )
                    
                    # Set and get
                    self.cache.set(key, config)
                    result = self.cache.get(key)
                    
                    if result:
                        results.append(result.key)
                    
                    # Random operations
                    if i % 3 == 0:
                        self.cache.invalidate(key)
                    elif i % 5 == 0:
                        self.cache.cleanup_expired()
                        
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Verify some results were collected
        self.assertGreater(len(results), 0)
    
    def test_background_cleanup(self):
        """Test background cleanup thread"""
        # Add entry with short TTL
        self.cache.set("test_key", self.sample_config, ttl=0.2)
        
        # Verify it's there
        result = self.cache.get("test_key")
        self.assertIsNotNone(result)
        
        # Wait for background cleanup to run
        time.sleep(0.8)  # Wait longer than cleanup interval
        
        # Entry should be cleaned up by background thread
        result = self.cache.get("test_key")
        self.assertIsNone(result)
    
    def test_lru_eviction(self):
        """Test LRU eviction strategy"""
        # Fill cache to capacity
        for i in range(5):
            config = ConfigurationValue(
                key=f"key_{i}",
                value=f"value_{i}",
                data_type="string",
                source=ConfigurationSource.DATABASE,
                requires_restart=False,
                last_updated=datetime.now(timezone.utc),
                cached_at=datetime.now(timezone.utc),
                ttl=300
            )
            self.cache.set(f"key_{i}", config)
            time.sleep(0.01)  # Small delay to ensure different access times
        
        # Access some entries to update their LRU status
        self.cache.get("key_1")  # Make key_1 more recently used
        self.cache.get("key_3")  # Make key_3 more recently used
        
        # Add new entry (should evict LRU)
        new_config = ConfigurationValue(
            key="new_key",
            value="new_value",
            data_type="string",
            source=ConfigurationSource.DATABASE,
            requires_restart=False,
            last_updated=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=300
        )
        self.cache.set("new_key", new_config)
        
        # Recently accessed entries should still be there
        self.assertIsNotNone(self.cache.get("key_1"))
        self.assertIsNotNone(self.cache.get("key_3"))
        self.assertIsNotNone(self.cache.get("new_key"))
        
        # Cache should still be at capacity
        stats = self.cache.get_stats()
        self.assertEqual(stats.total_keys, 5)
    
    def test_error_handling(self):
        """Test error handling in cache operations"""
        # Test with invalid operations that might cause errors
        
        # These should not raise exceptions
        result = self.cache.get("")  # Empty key
        self.assertIsNone(result)
        
        result = self.cache.get(None)  # None key - will cause error but handled
        self.assertIsNone(result)
        
        # Invalidate operations should handle errors gracefully
        success = self.cache.invalidate("")
        # Should return False but not crash
        
        # Clear should always work
        self.cache.clear()
        stats = self.cache.get_stats()
        self.assertEqual(stats.total_keys, 0)


if __name__ == '__main__':
    unittest.main()
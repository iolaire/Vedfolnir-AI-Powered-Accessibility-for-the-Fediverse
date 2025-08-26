# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance tests for storage management system.

Tests storage calculation performance with large file sets, caching effectiveness,
and system performance under various load conditions.
"""

import unittest
import tempfile
import shutil
import os
import time
import threading
import statistics
from unittest.mock import Mock, patch
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_monitor_service import StorageMonitorService, StorageMetrics
from storage_configuration_service import StorageConfigurationService
from storage_limit_enforcer import StorageLimitEnforcer


class TestStorageCalculationPerformance(unittest.TestCase):
    """Performance tests for storage calculation with large file sets"""
    
    def setUp(self):
        """Set up test fixtures for performance testing"""
        # Create temporary directory for test storage
        self.temp_dir = tempfile.mkdtemp()
        self.test_storage_dir = os.path.join(self.temp_dir, "storage", "images")
        os.makedirs(self.test_storage_dir, exist_ok=True)
        
        # Patch storage directory
        self.storage_dir_patcher = patch.object(
            StorageMonitorService, 'STORAGE_IMAGES_DIR', self.test_storage_dir
        )
        self.storage_dir_patcher.start()
        
        # Initialize services
        self.config_service = StorageConfigurationService()
        self.monitor_service = StorageMonitorService(config_service=self.config_service)
        
        # Performance tracking
        self.performance_results = {}
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.storage_dir_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_large_file_set(self, num_files: int, file_size_kb: int = 100):
        """Create a large set of test files for performance testing"""
        file_size_bytes = file_size_kb * 1024
        
        print(f"Creating {num_files} files of {file_size_kb}KB each...")
        start_time = time.time()
        
        for i in range(num_files):
            file_path = os.path.join(self.test_storage_dir, f"perf_test_{i:06d}.jpg")
            with open(file_path, 'wb') as f:
                f.write(b'0' * file_size_bytes)
            
            # Progress indicator for large sets
            if (i + 1) % 1000 == 0:
                print(f"Created {i + 1}/{num_files} files...")
        
        creation_time = time.time() - start_time
        print(f"File creation completed in {creation_time:.2f} seconds")
        return creation_time
    
    def measure_storage_calculation_time(self, description: str) -> float:
        """Measure time taken for storage calculation"""
        # Clear cache to ensure fresh calculation
        self.monitor_service._cache = {}
        
        start_time = time.time()
        metrics = self.monitor_service.get_storage_metrics()
        end_time = time.time()
        
        calculation_time = end_time - start_time
        
        print(f"{description}: {calculation_time:.4f} seconds")
        print(f"  - Total files processed: {len(list(Path(self.test_storage_dir).glob('*')))}")
        print(f"  - Total storage: {metrics.total_gb:.2f} GB")
        print(f"  - Usage percentage: {metrics.usage_percentage:.1f}%")
        
        return calculation_time
    
    def test_small_file_set_performance(self):
        """Test performance with small file set (100 files)"""
        num_files = 100
        self.create_large_file_set(num_files, file_size_kb=50)
        
        calculation_time = self.measure_storage_calculation_time(
            f"Storage calculation with {num_files} files"
        )
        
        # Should complete quickly for small sets
        self.assertLess(calculation_time, 1.0, "Small file set calculation should be under 1 second")
        self.performance_results['small_set'] = calculation_time
    
    def test_medium_file_set_performance(self):
        """Test performance with medium file set (1,000 files)"""
        num_files = 1000
        self.create_large_file_set(num_files, file_size_kb=100)
        
        calculation_time = self.measure_storage_calculation_time(
            f"Storage calculation with {num_files} files"
        )
        
        # Should complete reasonably quickly for medium sets
        self.assertLess(calculation_time, 5.0, "Medium file set calculation should be under 5 seconds")
        self.performance_results['medium_set'] = calculation_time
    
    def test_large_file_set_performance(self):
        """Test performance with large file set (5,000 files)"""
        num_files = 5000
        self.create_large_file_set(num_files, file_size_kb=200)
        
        calculation_time = self.measure_storage_calculation_time(
            f"Storage calculation with {num_files} files"
        )
        
        # Should complete within reasonable time for large sets
        self.assertLess(calculation_time, 15.0, "Large file set calculation should be under 15 seconds")
        self.performance_results['large_set'] = calculation_time
    
    def test_very_large_file_set_performance(self):
        """Test performance with very large file set (10,000 files)"""
        num_files = 10000
        self.create_large_file_set(num_files, file_size_kb=150)
        
        calculation_time = self.measure_storage_calculation_time(
            f"Storage calculation with {num_files} files"
        )
        
        # Should complete within acceptable time for very large sets
        self.assertLess(calculation_time, 30.0, "Very large file set calculation should be under 30 seconds")
        self.performance_results['very_large_set'] = calculation_time
    
    def test_caching_effectiveness(self):
        """Test caching mechanism effectiveness"""
        # Create test files
        num_files = 1000
        self.create_large_file_set(num_files, file_size_kb=100)
        
        # First calculation (cache miss)
        self.monitor_service._cache = {}
        start_time = time.time()
        metrics1 = self.monitor_service.get_storage_metrics()
        first_calculation_time = time.time() - start_time
        
        # Second calculation (cache hit)
        start_time = time.time()
        metrics2 = self.monitor_service.get_storage_metrics()
        second_calculation_time = time.time() - start_time
        
        print(f"First calculation (cache miss): {first_calculation_time:.4f} seconds")
        print(f"Second calculation (cache hit): {second_calculation_time:.4f} seconds")
        print(f"Cache speedup: {first_calculation_time / second_calculation_time:.1f}x")
        
        # Cached result should be much faster
        self.assertLess(second_calculation_time, first_calculation_time / 10, 
                       "Cached calculation should be at least 10x faster")
        
        # Results should be identical
        self.assertEqual(metrics1.total_bytes, metrics2.total_bytes)
        self.assertEqual(metrics1.total_gb, metrics2.total_gb)
        
        self.performance_results['cache_miss'] = first_calculation_time
        self.performance_results['cache_hit'] = second_calculation_time
    
    def test_concurrent_calculation_performance(self):
        """Test performance under concurrent access"""
        # Create test files
        num_files = 2000
        self.create_large_file_set(num_files, file_size_kb=100)
        
        # Clear cache
        self.monitor_service._cache = {}
        
        def calculate_storage():
            """Worker function for concurrent calculations"""
            start_time = time.time()
            metrics = self.monitor_service.get_storage_metrics()
            end_time = time.time()
            return end_time - start_time, metrics
        
        # Run concurrent calculations
        num_threads = 5
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(calculate_storage) for _ in range(num_threads)]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        calculation_times = [result[0] for result in results]
        metrics_list = [result[1] for result in results]
        
        avg_calculation_time = statistics.mean(calculation_times)
        max_calculation_time = max(calculation_times)
        min_calculation_time = min(calculation_times)
        
        print(f"Concurrent calculations ({num_threads} threads):")
        print(f"  - Total time: {total_time:.4f} seconds")
        print(f"  - Average calculation time: {avg_calculation_time:.4f} seconds")
        print(f"  - Min calculation time: {min_calculation_time:.4f} seconds")
        print(f"  - Max calculation time: {max_calculation_time:.4f} seconds")
        
        # All results should be consistent
        first_total_bytes = metrics_list[0].total_bytes
        for metrics in metrics_list:
            self.assertEqual(metrics.total_bytes, first_total_bytes, 
                           "All concurrent calculations should return same result")
        
        # Concurrent access shouldn't be significantly slower than single access
        self.assertLess(max_calculation_time, avg_calculation_time * 2, 
                       "Concurrent access shouldn't be more than 2x slower")
        
        self.performance_results['concurrent_avg'] = avg_calculation_time
        self.performance_results['concurrent_max'] = max_calculation_time
    
    def test_memory_usage_during_calculation(self):
        """Test memory usage during large file set calculations"""
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        
        # Create large file set
        num_files = 3000
        self.create_large_file_set(num_files, file_size_kb=200)
        
        # Measure memory before calculation
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform calculation
        self.monitor_service._cache = {}
        start_time = time.time()
        metrics = self.monitor_service.get_storage_metrics()
        calculation_time = time.time() - start_time
        
        # Measure memory after calculation
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before
        
        print(f"Memory usage during calculation:")
        print(f"  - Before: {memory_before:.1f} MB")
        print(f"  - After: {memory_after:.1f} MB")
        print(f"  - Increase: {memory_increase:.1f} MB")
        print(f"  - Calculation time: {calculation_time:.4f} seconds")
        print(f"  - Files processed: {num_files}")
        
        # Memory increase should be reasonable
        self.assertLess(memory_increase, 100, "Memory increase should be under 100MB")
        
        self.performance_results['memory_increase_mb'] = memory_increase
    
    def test_cache_expiration_performance(self):
        """Test performance impact of cache expiration"""
        # Create test files
        num_files = 1500
        self.create_large_file_set(num_files, file_size_kb=100)
        
        # Initial calculation
        self.monitor_service._cache = {}
        initial_time = self.measure_storage_calculation_time("Initial calculation")
        
        # Cached calculation
        cached_time = self.measure_storage_calculation_time("Cached calculation")
        
        # Simulate cache expiration by clearing cache
        self.monitor_service._cache = {}
        
        # Post-expiration calculation
        expired_time = self.measure_storage_calculation_time("Post-expiration calculation")
        
        print(f"Cache expiration performance:")
        print(f"  - Initial: {initial_time:.4f}s")
        print(f"  - Cached: {cached_time:.4f}s")
        print(f"  - Post-expiration: {expired_time:.4f}s")
        
        # Post-expiration should be similar to initial
        self.assertLess(abs(expired_time - initial_time), initial_time * 0.2, 
                       "Post-expiration time should be similar to initial time")
        
        # Cached should be much faster
        self.assertLess(cached_time, initial_time / 5, 
                       "Cached calculation should be at least 5x faster")
    
    def test_directory_structure_performance(self):
        """Test performance with different directory structures"""
        # Test flat structure (all files in one directory)
        num_files = 1000
        self.create_large_file_set(num_files, file_size_kb=100)
        
        flat_time = self.measure_storage_calculation_time("Flat directory structure")
        
        # Clean up and create nested structure
        shutil.rmtree(self.test_storage_dir)
        os.makedirs(self.test_storage_dir, exist_ok=True)
        
        # Create nested directory structure
        files_per_subdir = 100
        num_subdirs = num_files // files_per_subdir
        
        for subdir_idx in range(num_subdirs):
            subdir_path = os.path.join(self.test_storage_dir, f"subdir_{subdir_idx:03d}")
            os.makedirs(subdir_path, exist_ok=True)
            
            for file_idx in range(files_per_subdir):
                file_path = os.path.join(subdir_path, f"nested_file_{file_idx:03d}.jpg")
                with open(file_path, 'wb') as f:
                    f.write(b'0' * (100 * 1024))  # 100KB
        
        nested_time = self.measure_storage_calculation_time("Nested directory structure")
        
        print(f"Directory structure performance comparison:")
        print(f"  - Flat structure: {flat_time:.4f}s")
        print(f"  - Nested structure: {nested_time:.4f}s")
        print(f"  - Difference: {abs(nested_time - flat_time):.4f}s")
        
        # Performance should be similar regardless of structure
        self.assertLess(abs(nested_time - flat_time), max(flat_time, nested_time) * 0.5, 
                       "Directory structure shouldn't significantly impact performance")
        
        self.performance_results['flat_structure'] = flat_time
        self.performance_results['nested_structure'] = nested_time
    
    def test_performance_summary(self):
        """Print performance summary"""
        if self.performance_results:
            print("\n" + "="*60)
            print("STORAGE PERFORMANCE TEST SUMMARY")
            print("="*60)
            
            for test_name, result in self.performance_results.items():
                if isinstance(result, float):
                    print(f"{test_name:30}: {result:.4f} seconds")
                else:
                    print(f"{test_name:30}: {result}")
            
            print("="*60)


class TestStorageEnforcerPerformance(unittest.TestCase):
    """Performance tests for storage limit enforcer"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock Redis for performance testing
        self.redis_data = {}
        self.mock_redis = Mock()
        self.mock_redis.ping.return_value = True
        
        def mock_get(key):
            return self.redis_data.get(key)
        
        def mock_set(key, value):
            self.redis_data[key] = value
            return True
        
        self.mock_redis.get = mock_get
        self.mock_redis.set = mock_set
        
        # Initialize services
        self.config_service = StorageConfigurationService()
        self.monitor_service = Mock()
        
        with patch('storage_limit_enforcer.redis.Redis', return_value=self.mock_redis):
            self.enforcer = StorageLimitEnforcer(
                config_service=self.config_service,
                monitor_service=self.monitor_service
            )
    
    def test_enforcement_check_performance(self):
        """Test performance of storage enforcement checks"""
        # Mock storage metrics
        mock_metrics = Mock()
        mock_metrics.is_limit_exceeded = False
        mock_metrics.total_gb = 8.5
        mock_metrics.limit_gb = 10.0
        mock_metrics.usage_percentage = 85.0
        
        self.monitor_service.get_storage_metrics.return_value = mock_metrics
        
        # Measure single check performance
        start_time = time.time()
        result = self.enforcer.check_storage_before_generation()
        single_check_time = time.time() - start_time
        
        print(f"Single enforcement check: {single_check_time:.6f} seconds")
        
        # Measure multiple checks performance
        num_checks = 1000
        start_time = time.time()
        
        for _ in range(num_checks):
            self.enforcer.check_storage_before_generation()
        
        total_time = time.time() - start_time
        avg_check_time = total_time / num_checks
        
        print(f"Average check time ({num_checks} checks): {avg_check_time:.6f} seconds")
        print(f"Checks per second: {num_checks / total_time:.0f}")
        
        # Performance should be very fast
        self.assertLess(avg_check_time, 0.001, "Average check should be under 1ms")
        self.assertGreater(num_checks / total_time, 1000, "Should handle >1000 checks per second")
    
    def test_concurrent_enforcement_performance(self):
        """Test concurrent enforcement check performance"""
        # Mock storage metrics
        mock_metrics = Mock()
        mock_metrics.is_limit_exceeded = False
        mock_metrics.total_gb = 8.5
        mock_metrics.limit_gb = 10.0
        mock_metrics.usage_percentage = 85.0
        
        self.monitor_service.get_storage_metrics.return_value = mock_metrics
        
        def enforcement_worker():
            """Worker function for concurrent enforcement checks"""
            start_time = time.time()
            for _ in range(100):
                self.enforcer.check_storage_before_generation()
            return time.time() - start_time
        
        # Run concurrent enforcement checks
        num_threads = 10
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(enforcement_worker) for _ in range(num_threads)]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        total_checks = num_threads * 100
        
        avg_worker_time = statistics.mean(results)
        checks_per_second = total_checks / total_time
        
        print(f"Concurrent enforcement performance:")
        print(f"  - Total checks: {total_checks}")
        print(f"  - Total time: {total_time:.4f} seconds")
        print(f"  - Average worker time: {avg_worker_time:.4f} seconds")
        print(f"  - Checks per second: {checks_per_second:.0f}")
        
        # Should handle high concurrent load
        self.assertGreater(checks_per_second, 5000, "Should handle >5000 concurrent checks per second")


if __name__ == '__main__':
    unittest.main()
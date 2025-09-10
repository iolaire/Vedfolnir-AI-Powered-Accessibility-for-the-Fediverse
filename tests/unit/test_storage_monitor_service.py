# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for StorageMonitorService.

Tests storage calculation with various file structures, caching mechanism,
error handling for missing directories and permission issues.
"""

import unittest
import tempfile
import shutil
import os
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.storage.components.storage_monitor_service import StorageMonitorService, StorageMetrics
from app.services.storage.components.storage_configuration_service import StorageConfigurationService


class TestStorageMonitorService(unittest.TestCase):
    """Test cases for StorageMonitorService"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock configuration service
        self.mock_config = Mock(spec=StorageConfigurationService)
        self.mock_config.get_max_storage_gb.return_value = 10.0
        self.mock_config.get_warning_threshold_gb.return_value = 8.0
        
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_storage_dir = os.path.join(self.temp_dir, "storage", "images")
        os.makedirs(self.test_storage_dir, exist_ok=True)
        
        # Patch the storage directory path
        self.storage_dir_patcher = patch.object(
            StorageMonitorService, 'STORAGE_IMAGES_DIR', self.test_storage_dir
        )
        self.storage_dir_patcher.start()
        
        # Create service instance
        self.service = StorageMonitorService(config_service=self.mock_config)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.storage_dir_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, filename: str, size_bytes: int) -> str:
        """
        Create a test file with specified size.
        
        Args:
            filename: Name of the file to create
            size_bytes: Size of the file in bytes
            
        Returns:
            str: Path to the created file
        """
        file_path = os.path.join(self.test_storage_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(b'0' * size_bytes)
        return file_path
    
    def _create_test_directory_structure(self) -> dict:
        """
        Create a complex directory structure for testing.
        
        Returns:
            dict: Information about created files and their sizes
        """
        # Create subdirectories
        subdir1 = os.path.join(self.test_storage_dir, "subdir1")
        subdir2 = os.path.join(self.test_storage_dir, "subdir2")
        nested_dir = os.path.join(subdir1, "nested")
        
        os.makedirs(subdir1, exist_ok=True)
        os.makedirs(subdir2, exist_ok=True)
        os.makedirs(nested_dir, exist_ok=True)
        
        # Create files with known sizes
        files = {
            "root_file.jpg": 1024,  # 1KB
            "subdir1/image1.png": 2048,  # 2KB
            "subdir1/image2.jpg": 4096,  # 4KB
            "subdir2/large_image.png": 1024 * 1024,  # 1MB
            "subdir1/nested/small.jpg": 512,  # 512 bytes
        }
        
        total_size = 0
        for relative_path, size in files.items():
            full_path = os.path.join(self.test_storage_dir, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(b'0' * size)
            total_size += size
        
        return {
            'files': files,
            'total_size': total_size,
            'file_count': len(files)
        }
    
    def test_empty_directory_calculation(self):
        """Test storage calculation with empty directory"""
        total_bytes = self.service.calculate_total_storage_bytes()
        self.assertEqual(total_bytes, 0)
        
        usage_gb = self.service.get_storage_usage_gb()
        self.assertEqual(usage_gb, 0.0)
        
        usage_percentage = self.service.get_storage_usage_percentage()
        self.assertEqual(usage_percentage, 0.0)
    
    def test_single_file_calculation(self):
        """Test storage calculation with single file"""
        file_size = 1024 * 1024  # 1MB
        self._create_test_file("test_image.jpg", file_size)
        
        total_bytes = self.service.calculate_total_storage_bytes()
        self.assertEqual(total_bytes, file_size)
        
        expected_gb = file_size / (1024 ** 3)
        usage_gb = self.service.get_storage_usage_gb()
        self.assertAlmostEqual(usage_gb, expected_gb, places=6)
    
    def test_multiple_files_calculation(self):
        """Test storage calculation with multiple files"""
        file_sizes = [1024, 2048, 4096, 8192]  # Various sizes
        total_expected = sum(file_sizes)
        
        for i, size in enumerate(file_sizes):
            self._create_test_file(f"file_{i}.jpg", size)
        
        total_bytes = self.service.calculate_total_storage_bytes()
        self.assertEqual(total_bytes, total_expected)
    
    def test_recursive_directory_calculation(self):
        """Test storage calculation with nested directory structure"""
        structure_info = self._create_test_directory_structure()
        
        total_bytes = self.service.calculate_total_storage_bytes()
        self.assertEqual(total_bytes, structure_info['total_size'])
        
        # Verify all files are counted
        expected_gb = structure_info['total_size'] / (1024 ** 3)
        usage_gb = self.service.get_storage_usage_gb()
        self.assertAlmostEqual(usage_gb, expected_gb, places=6)
    
    def test_storage_limit_detection(self):
        """Test storage limit exceeded detection"""
        # Create file that exceeds the 10GB limit
        large_file_size = int(11 * 1024 ** 3)  # 11GB (exceeds 10GB limit)
        
        # Mock the calculation to avoid creating huge file
        with patch.object(self.service, 'calculate_total_storage_bytes', return_value=large_file_size):
            self.assertTrue(self.service.is_storage_limit_exceeded())
            
            usage_percentage = self.service.get_storage_usage_percentage()
            self.assertGreater(usage_percentage, 100.0)
    
    def test_warning_threshold_detection(self):
        """Test warning threshold exceeded detection"""
        # Create file that exceeds 8GB warning threshold but not 10GB limit
        warning_file_size = int(9 * 1024 ** 3)  # 9GB (exceeds 8GB warning)
        
        # Mock the calculation
        with patch.object(self.service, 'calculate_total_storage_bytes', return_value=warning_file_size):
            self.assertTrue(self.service.is_warning_threshold_exceeded())
            self.assertFalse(self.service.is_storage_limit_exceeded())
            
            usage_percentage = self.service.get_storage_usage_percentage()
            self.assertGreater(usage_percentage, 80.0)
            self.assertLess(usage_percentage, 100.0)
    
    def test_caching_mechanism(self):
        """Test 5-minute caching mechanism"""
        # Create test file
        file_size = 1024 * 1024  # 1MB
        self._create_test_file("cached_test.jpg", file_size)
        
        # First call should calculate and cache
        metrics1 = self.service.get_storage_metrics()
        self.assertEqual(metrics1.total_bytes, file_size)
        
        # Add another file
        self._create_test_file("new_file.jpg", file_size)
        
        # Second call should use cache (not see new file)
        metrics2 = self.service.get_storage_metrics()
        self.assertEqual(metrics2.total_bytes, file_size)  # Still old value
        
        # Invalidate cache and try again
        self.service.invalidate_cache()
        metrics3 = self.service.get_storage_metrics()
        self.assertEqual(metrics3.total_bytes, file_size * 2)  # Now sees both files
    
    def test_cache_expiration(self):
        """Test cache expiration after 5 minutes"""
        # Create test file
        file_size = 1024 * 1024  # 1MB
        self._create_test_file("expire_test.jpg", file_size)
        
        # Get initial metrics
        metrics1 = self.service.get_storage_metrics()
        self.assertEqual(metrics1.total_bytes, file_size)
        
        # Mock time to simulate cache expiration
        future_time = datetime.now() + timedelta(minutes=6)
        with patch('storage_monitor_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_time
            
            # Add new file
            self._create_test_file("new_expire_test.jpg", file_size)
            
            # Should recalculate due to expired cache
            metrics2 = self.service.get_storage_metrics()
            self.assertEqual(metrics2.total_bytes, file_size * 2)
    
    def test_missing_directory_handling(self):
        """Test handling of missing storage directory"""
        # Remove the storage directory
        shutil.rmtree(self.test_storage_dir)
        
        # Service should handle missing directory gracefully
        total_bytes = self.service.calculate_total_storage_bytes()
        self.assertEqual(total_bytes, 0)
        
        # Directory should be recreated
        self.assertTrue(os.path.exists(self.test_storage_dir))
    
    def test_permission_error_handling(self):
        """Test handling of permission errors"""
        # Create test file first
        file_size = 1024
        self._create_test_file("permission_test.jpg", file_size)
        
        # Get initial metrics to populate cache
        initial_metrics = self.service.get_storage_metrics()
        self.assertEqual(initial_metrics.total_bytes, file_size)
        
        # Mock permission error
        with patch('os.walk', side_effect=PermissionError("Access denied")):
            # Should use cached value
            total_bytes = self.service.calculate_total_storage_bytes()
            self.assertEqual(total_bytes, file_size)
    
    def test_io_error_with_retry(self):
        """Test I/O error handling with retry mechanism"""
        file_size = 1024
        self._create_test_file("io_test.jpg", file_size)
        
        # Mock I/O error on first call, success on retry
        call_count = 0
        original_walk = os.walk
        
        def mock_walk_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("I/O error")
            else:
                # Return actual walk results on retry
                return original_walk(*args, **kwargs)
        
        with patch('os.walk', side_effect=mock_walk_with_retry):
            total_bytes = self.service.calculate_total_storage_bytes()
            self.assertEqual(total_bytes, file_size)
            self.assertEqual(call_count, 2)  # Verify retry occurred
    
    def test_io_error_with_failed_retry(self):
        """Test I/O error handling when retry also fails"""
        file_size = 1024
        self._create_test_file("io_fail_test.jpg", file_size)
        
        # Get initial metrics to populate cache
        initial_metrics = self.service.get_storage_metrics()
        self.assertEqual(initial_metrics.total_bytes, file_size)
        
        # Mock persistent I/O error
        with patch('os.walk', side_effect=OSError("Persistent I/O error")):
            # Should use cached value
            total_bytes = self.service.calculate_total_storage_bytes()
            self.assertEqual(total_bytes, file_size)
    
    def test_io_error_without_cache_safe_mode(self):
        """Test I/O error handling without cache (safe mode)"""
        # Don't populate cache
        
        # Mock persistent I/O error
        with patch('os.walk', side_effect=OSError("I/O error")):
            # Should return safe mode value (over limit)
            total_bytes = self.service.calculate_total_storage_bytes()
            expected_safe_bytes = int(10.0 * (1024 ** 3) * 1.1)  # 110% of 10GB limit
            self.assertEqual(total_bytes, expected_safe_bytes)
    
    def test_storage_metrics_comprehensive(self):
        """Test comprehensive storage metrics calculation"""
        # Create test structure
        structure_info = self._create_test_directory_structure()
        
        metrics = self.service.get_storage_metrics()
        
        # Verify all fields
        self.assertEqual(metrics.total_bytes, structure_info['total_size'])
        self.assertAlmostEqual(metrics.total_gb, structure_info['total_size'] / (1024 ** 3), places=6)
        self.assertEqual(metrics.limit_gb, 10.0)
        self.assertAlmostEqual(metrics.usage_percentage, (metrics.total_gb / 10.0) * 100.0, places=2)
        self.assertFalse(metrics.is_limit_exceeded)  # Small test files won't exceed 10GB
        self.assertFalse(metrics.is_warning_exceeded)  # Small test files won't exceed 8GB
        self.assertIsInstance(metrics.last_calculated, datetime)
    
    def test_cache_info(self):
        """Test cache information reporting"""
        # Initially no cache
        cache_info = self.service.get_cache_info()
        self.assertFalse(cache_info['has_cache'])
        self.assertFalse(cache_info['is_valid'])
        
        # Create cache
        self._create_test_file("cache_info_test.jpg", 1024)
        self.service.get_storage_metrics()
        
        # Now should have valid cache
        cache_info = self.service.get_cache_info()
        self.assertTrue(cache_info['has_cache'])
        self.assertTrue(cache_info['is_valid'])
        self.assertGreater(cache_info['cache_expires_in_seconds'], 0)
        self.assertEqual(cache_info['cache_duration_seconds'], 300)  # 5 minutes
    
    def test_zero_storage_limit_handling(self):
        """Test handling of zero or negative storage limits"""
        # Mock zero storage limit
        self.mock_config.get_max_storage_gb.return_value = 0.0
        
        usage_percentage = self.service.get_storage_usage_percentage()
        self.assertEqual(usage_percentage, 100.0)  # Should assume limit exceeded
    
    def test_metrics_serialization(self):
        """Test StorageMetrics to_dict method"""
        # Create test file and get metrics
        self._create_test_file("serialize_test.jpg", 1024)
        metrics = self.service.get_storage_metrics()
        
        # Test serialization
        metrics_dict = metrics.to_dict()
        
        # Verify all fields are present
        expected_fields = [
            'total_bytes', 'total_gb', 'limit_gb', 'usage_percentage',
            'is_limit_exceeded', 'is_warning_exceeded', 'last_calculated'
        ]
        
        for field in expected_fields:
            self.assertIn(field, metrics_dict)
        
        # Verify types
        self.assertIsInstance(metrics_dict['total_bytes'], int)
        self.assertIsInstance(metrics_dict['total_gb'], float)
        self.assertIsInstance(metrics_dict['is_limit_exceeded'], bool)
        self.assertIsInstance(metrics_dict['last_calculated'], str)  # ISO format
    
    def test_large_file_structure(self):
        """Test with larger file structure (performance test)"""
        # Create many small files to test performance
        num_files = 100
        file_size = 1024  # 1KB each
        
        for i in range(num_files):
            subdir = f"subdir_{i // 10}"  # 10 files per subdirectory
            subdir_path = os.path.join(self.test_storage_dir, subdir)
            os.makedirs(subdir_path, exist_ok=True)
            
            file_path = os.path.join(subdir_path, f"file_{i}.jpg")
            with open(file_path, 'wb') as f:
                f.write(b'0' * file_size)
        
        # Measure calculation time
        start_time = time.time()
        total_bytes = self.service.calculate_total_storage_bytes()
        calculation_time = time.time() - start_time
        
        # Verify results
        expected_total = num_files * file_size
        self.assertEqual(total_bytes, expected_total)
        
        # Performance should be reasonable (less than 1 second for 100 files)
        self.assertLess(calculation_time, 1.0)
    
    def test_symlink_handling(self):
        """Test handling of symbolic links"""
        # Create a regular file
        file_size = 1024
        regular_file = self._create_test_file("regular.jpg", file_size)
        
        # Create a symlink to the file
        symlink_path = os.path.join(self.test_storage_dir, "symlink.jpg")
        try:
            os.symlink(regular_file, symlink_path)
            
            # Should count the file size, not the symlink size
            total_bytes = self.service.calculate_total_storage_bytes()
            self.assertEqual(total_bytes, file_size * 2)  # Regular file + symlink target
            
        except OSError:
            # Skip test if symlinks not supported on this system
            self.skipTest("Symbolic links not supported on this system")


if __name__ == '__main__':
    unittest.main()